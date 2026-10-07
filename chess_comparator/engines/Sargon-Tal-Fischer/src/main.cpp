#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <fstream>
#include <filesystem>
#include <iterator>
#include <limits>
#include <mutex>
#include <random>
#include <sstream>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>
#include "book_format.h"
#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#elif defined(__linux__)
#include <unistd.h>
#elif defined(__APPLE__)
#include <mach-o/dyld.h>
#endif

namespace {
using Clock = std::chrono::steady_clock;
constexpr int MAX_PLY = 128;
constexpr int INF = 32000;
constexpr int MATE = 30000;
constexpr int MAX_DEPTH = 20;

enum Bound : uint8_t { EXACT, LOWER, UPPER };
struct TTEntry {
    uint64_t key = 0;
    int16_t score = 0;
    int8_t depth = -1;
    uint8_t bound = UPPER;
    thc::Move best{};
    uint8_t age = 0;
};
static_assert(sizeof(TTEntry) <= 24, "Unexpected hash entry size");

std::mutex output_mutex;
void output(const std::string& line) {
    std::lock_guard<std::mutex> lock(output_mutex);
    std::cout << line << std::flush;
}

int piece_value(char p) {
    switch (std::tolower(static_cast<unsigned char>(p))) {
    case 'p': return 100;
    case 'n': case 'b': return 310;
    case 'r': return 500;
    case 'q': return 900;
    case 'k': return 20000;
    default: return 0;
    }
}

int promotion_value(const thc::Move& m) {
    switch (m.special) {
    case thc::SPECIAL_PROMOTION_QUEEN: return 900;
    case thc::SPECIAL_PROMOTION_ROOK: return 500;
    case thc::SPECIAL_PROMOTION_BISHOP: return 310;
    case thc::SPECIAL_PROMOTION_KNIGHT: return 310;
    default: return 0;
    }
}

bool promotion(const thc::Move& m) {
    return m.special == thc::SPECIAL_PROMOTION_QUEEN ||
           m.special == thc::SPECIAL_PROMOTION_ROOK ||
           m.special == thc::SPECIAL_PROMOTION_BISHOP ||
           m.special == thc::SPECIAL_PROMOTION_KNIGHT;
}

uint64_t mix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}
uint64_t position_key(thc::ChessPosition& p) {
    uint64_t k = p.Hash64Calculate();
    const unsigned rights = (p.wking ? 1u : 0u) | (p.wqueen ? 2u : 0u) |
                            (p.bking ? 4u : 0u) | (p.bqueen ? 8u : 0u);
    k ^= mix64(0x534152474f4eULL + rights + (p.white ? 0x100u : 0u));
    if (p.enpassant_target != thc::SQUARE_INVALID)
        k ^= mix64(0x45504ULL + static_cast<unsigned>(p.enpassant_target));
    k ^= mix64(0x48414c46ULL + static_cast<unsigned>(std::min(p.half_move_clock, 100)));
    return k;
}

std::filesystem::path executable_directory() {
#ifdef _WIN32
    char path[32768]{};
    const DWORD length = GetModuleFileNameA(nullptr, path, static_cast<DWORD>(sizeof(path)));
    if (length > 0 && length < sizeof(path)) return std::filesystem::path(path).parent_path();
#elif defined(__linux__)
    char path[4096]{};
    const ssize_t length = readlink("/proc/self/exe", path, sizeof(path)-1);
    if (length > 0) { path[length] = '\0'; return std::filesystem::path(path).parent_path(); }
#elif defined(__APPLE__)
    char path[4096]{};
    uint32_t size = static_cast<uint32_t>(sizeof(path));
    if (_NSGetExecutablePath(path, &size) == 0) return std::filesystem::path(path).parent_path();
#endif
    return {};
}

struct SearchLimits {
    int depth = 0;
    int movetime = 0;
    int wtime = -1, btime = -1, winc = 0, binc = 0, movestogo = 30;
    bool infinite = false;
};

class Engine {
public:
    thc::ChessRules board;
    int hash_mb = 16;
    int max_depth = MAX_DEPTH;
    int aggression = 72; // Tal initiative balanced by Fischer-style material discipline.
    std::string style = "Tal-Fischer";
    int move_overhead = 40;
    bool own_book = true;
    bool book_random = true;
    int book_depth = 24;
    std::string book_file = "Sargon-Tal-Fischer.bin";
    struct BookMove { std::string uci; uint16_t weight; };
    std::unordered_map<uint64_t, std::vector<BookMove>> book;
    std::mt19937_64 book_rng{std::random_device{}()};
    std::atomic<bool> stop{false};
    std::thread worker;
    std::vector<TTEntry> tt;
    uint8_t age = 0;
    uint64_t nodes = 0;
    size_t tt_used = 0;
    Clock::time_point start_time, deadline;
    bool has_deadline = false;
    std::array<std::array<thc::Move, MAX_PLY>, MAX_PLY> pv{};
    std::array<int, MAX_PLY> pv_len{};
    std::array<std::array<thc::Move, 2>, MAX_PLY> killers{};
    int history[2][64][64]{};
    int seldepth = 0;

    Engine() { resize_hash(hash_mb); load_book(); }
    ~Engine() { stop_search(); }

    void resize_hash(int mb) {
        hash_mb = std::max(1, std::min(32, mb));
        const size_t bytes = static_cast<size_t>(hash_mb) * 1024 * 1024;
        const size_t count = std::max<size_t>(1, bytes / sizeof(TTEntry));
        std::vector<TTEntry> replacement(count);
        tt.swap(replacement);
        tt_used = 0;
    }
    void clear_hash() {
        std::fill(tt.begin(), tt.end(), TTEntry{});
        tt_used = 0;
        ++age;
    }
    bool load_book() {
        book.clear();
        std::ifstream in(book_file, std::ios::binary);
        if (!in && !std::filesystem::path(book_file).is_absolute()) {
            const auto adjacent = executable_directory() / book_file;
            in.clear();
            in.open(adjacent, std::ios::binary);
        }
        if (!in) return false;
        char magic[sizeof(sargon_book::MAGIC)];
        uint32_t version = 0, count = 0;
        if (!in.read(magic, sizeof(magic)) ||
            !std::equal(std::begin(magic), std::end(magic), std::begin(sargon_book::MAGIC)) ||
            !sargon_book::read_u32(in, version) || version != sargon_book::VERSION ||
            !sargon_book::read_u32(in, count) || count > sargon_book::MAX_RECORDS) {
            book.clear(); return false;
        }
        for (uint32_t i = 0; i < count; ++i) {
            uint64_t key = 0; char move[6]{}; uint16_t weight = 0;
            if (!sargon_book::read_u64(in, key) || !in.read(move, sizeof(move)) ||
                !sargon_book::read_u16(in, weight)) { book.clear(); return false; }
            move[sizeof(move)-1] = '\0';
            if (move[0] && weight) book[key].push_back({move, weight});
        }
        return true;
    }
    std::string book_move(thc::ChessRules root, uint16_t& chosen_weight) {
        chosen_weight = 0;
        if (!own_book || book.empty()) return {};
        const int ply = std::max(0, (root.full_move_count - 1) * 2 + (root.white ? 0 : 1));
        if (ply >= book_depth) return {};
        const auto it = book.find(sargon_book::position_key(root));
        if (it == book.end()) return {};
        std::vector<thc::Move> legal;
        root.GenLegalMoveList(legal);
        std::vector<BookMove> candidates;
        uint64_t total = 0;
        for (const auto& candidate : it->second) {
            const bool is_legal = std::any_of(legal.begin(), legal.end(), [&](const thc::Move& m) {
                thc::Move move = m;
                return move.TerseOut() == candidate.uci;
            });
            if (is_legal) { candidates.push_back(candidate); total += candidate.weight; }
        }
        if (candidates.empty()) return {};
        size_t selected = 0;
        if (book_random && total > 0) {
            std::uniform_int_distribution<uint64_t> pick(1, total);
            uint64_t value = pick(book_rng);
            for (size_t i = 0; i < candidates.size(); ++i) {
                if (value <= candidates[i].weight) { selected = i; break; }
                value -= candidates[i].weight;
            }
        } else {
            for (size_t i = 1; i < candidates.size(); ++i)
                if (candidates[i].weight > candidates[selected].weight) selected = i;
        }
        chosen_weight = candidates[selected].weight;
        return candidates[selected].uci;
    }
    void stop_search() {
        stop.store(true, std::memory_order_relaxed);
        if (worker.joinable()) worker.join();
    }
    bool in_check(thc::ChessRules& p) const {
        const thc::Square k = p.white ? p.wking_square : p.bking_square;
        return p.AttackedSquare(k, !p.white);
    }
    int king_pressure(thc::ChessRules& p, bool white_attacker) const {
        const thc::Square enemy_king = white_attacker ? p.bking_square : p.wking_square;
        const int kr = static_cast<int>(enemy_king) / 8;
        const int kf = static_cast<int>(enemy_king) % 8;
        int attacked_ring = 0, nearby_force = 0;
        for (int r = std::max(0, kr - 1); r <= std::min(7, kr + 1); ++r) {
            for (int f = std::max(0, kf - 1); f <= std::min(7, kf + 1); ++f) {
                int sq = r * 8 + f;
                if (p.AttackedSquare(static_cast<thc::Square>(sq), white_attacker)) ++attacked_ring;
            }
        }
        for (int sq = 0; sq < 64; ++sq) {
            char piece = p.squares[sq];
            if (piece == ' ' || ((piece >= 'A' && piece <= 'Z') != white_attacker)) continue;
            int distance = std::max(std::abs(sq / 8 - kr), std::abs(sq % 8 - kf));
            if (distance > 3 || distance == 0) continue;
            int weight = piece_value(piece);
            int unit = (weight >= 900 ? 5 : weight >= 500 ? 4 : weight >= 300 ? 4 : 2);
            nearby_force += unit * (4 - distance);
        }
        int open_lines = 0;
        for (int f = std::max(0, kf - 1); f <= std::min(7, kf + 1); ++f) {
            bool friendly_pawn = false, enemy_pawn = false, heavy_attacker = false;
            for (int r = 0; r < 8; ++r) {
                char x = p.squares[r * 8 + f];
                if (x == (white_attacker ? 'P' : 'p')) friendly_pawn = true;
                if (x == (white_attacker ? 'p' : 'P')) enemy_pawn = true;
                if (x == (white_attacker ? 'R' : 'r') || x == (white_attacker ? 'Q' : 'q')) heavy_attacker = true;
            }
            if (!friendly_pawn && heavy_attacker) open_lines += enemy_pawn ? 1 : 2;
        }
        int raw = attacked_ring * 7 + nearby_force * 2 + open_lines * 8;
        int style_weight = style == "Tal" ? 100 : style == "Fischer" ? 52 : 76;
        return std::min(110, raw) * aggression * style_weight / 10000;
    }
    int imbalance(const thc::ChessRules& p) const {
        int white_b = 0, black_b = 0;
        for (int i = 0; i < 64; ++i) {
            if (p.squares[i] == 'B') ++white_b;
            if (p.squares[i] == 'b') ++black_b;
        }
        int score = (white_b >= 2 ? 24 : 0) - (black_b >= 2 ? 24 : 0);
        for (int f = 0; f < 8; ++f) {
            bool wp = false, bp = false;
            for (int r = 0; r < 8; ++r) { wp |= p.squares[r*8+f] == 'P'; bp |= p.squares[r*8+f] == 'p'; }
            if (!wp && !bp) {
                for (int r = 0; r < 8; ++r) {
                    char x = p.squares[r*8+f];
                    if (x == 'R') score += 7;
                    else if (x == 'Q') score += 5;
                    else if (x == 'r') score -= 7;
                    else if (x == 'q') score -= 5;
                }
            }
        }
        return score;
    }
    int evaluate(thc::ChessRules& p) {
        thc::ChessEvaluation ev(p);
        int material = 0, positional = 0;
        ev.EvaluateLeaf(material, positional);
        int score = (material + positional) * 10; // the source evaluator uses tenths of a pawn.
        score += king_pressure(p, true) - king_pressure(p, false);
        score += imbalance(p);
        int initiative = style == "Tal" ? 12 : style == "Fischer" ? 4 : 8;
        score += p.white ? initiative : -initiative;
        return p.white ? score : -score;
    }
    bool poll_stop() {
        if (stop.load(std::memory_order_relaxed)) return true;
        if ((nodes & 1023ULL) == 0 && has_deadline && Clock::now() >= deadline) {
            stop.store(true, std::memory_order_relaxed);
            return true;
        }
        return false;
    }
    int score_to_tt(int score, int ply) const {
        if (score > MATE - MAX_PLY) return score + ply;
        if (score < -MATE + MAX_PLY) return score - ply;
        return score;
    }
    int score_from_tt(int score, int ply) const {
        if (score > MATE - MAX_PLY) return score - ply;
        if (score < -MATE + MAX_PLY) return score + ply;
        return score;
    }
    int move_score(const thc::ChessRules& p, const thc::Move& m, const thc::Move& ttmove, int ply) const {
        if (m == ttmove) return 2000000;
        if (m.capture != ' ') return 1000000 + piece_value(static_cast<char>(m.capture)) * 16 - piece_value(p.squares[m.src]);
        if (promotion(m)) return 900000 + promotion_value(m);
        if (ply < MAX_PLY && m == killers[ply][0]) return 800000;
        if (ply < MAX_PLY && m == killers[ply][1]) return 700000;
        return history[p.white ? 0 : 1][m.src][m.dst];
    }
    int quiescence(thc::ChessRules& p, int alpha, int beta, int ply, int qply) {
        ++nodes;
        if (poll_stop() || ply >= MAX_PLY - 1) return evaluate(p);
        seldepth = std::max(seldepth, ply);
        const bool check = in_check(p);
        int stand = evaluate(p);
        if (!check) {
            if (stand >= beta) return beta;
            if (stand > alpha) alpha = stand;
            if (qply >= 8) return alpha;
        }
        std::vector<thc::Move> moves;
        p.GenLegalMoveList(moves);
        if (moves.empty()) return check ? -MATE + ply : 0;
        if (p.half_move_clock >= 100 || p.GetRepetitionCount() >= 3) return 0;
        if (check && qply >= 10) return stand - 80;
        std::stable_sort(moves.begin(), moves.end(), [&](const thc::Move& a, const thc::Move& b) {
            int sa = a.capture != ' ' ? 1000 + piece_value(static_cast<char>(a.capture)) - piece_value(p.squares[a.src])/10 : promotion(a) ? 800 + promotion_value(a) : 0;
            int sb = b.capture != ' ' ? 1000 + piece_value(static_cast<char>(b.capture)) - piece_value(p.squares[b.src])/10 : promotion(b) ? 800 + promotion_value(b) : 0;
            return sa > sb;
        });
        for (auto m : moves) {
            if (!check && m.capture == ' ' && !promotion(m)) {
                if (qply >= 2) continue;
                p.PushMove(m);
                bool gives_check = in_check(p);
                if (!gives_check) { p.PopMove(m); continue; }
                int score = -quiescence(p, -beta, -alpha, ply+1, qply+1);
                p.PopMove(m);
                if (score >= beta) return beta;
                if (score > alpha) alpha = score;
                if (poll_stop()) return alpha;
                continue;
            }
            p.PushMove(m);
            int score = -quiescence(p, -beta, -alpha, ply+1, qply+1);
            p.PopMove(m);
            if (score >= beta) return beta;
            if (score > alpha) alpha = score;
            if (poll_stop()) return alpha;
        }
        return alpha;
    }
    int search(thc::ChessRules& p, int depth, int alpha, int beta, int ply, int extensions) {
        if (poll_stop() || ply >= MAX_PLY - 1) return evaluate(p);
        ++nodes;
        seldepth = std::max(seldepth, ply);
        pv_len[ply] = 0;
        if (depth <= 0) return quiescence(p, alpha, beta, ply, 0);
        if (p.GetRepetitionCount() >= 3) return 0;
        if (p.half_move_clock >= 100) {
            if (!in_check(p)) return 0;
            std::vector<thc::Move> draw_test; p.GenLegalMoveList(draw_test);
            if (draw_test.empty()) return -MATE + ply;
            return 0;
        }
        const int original_alpha = alpha;
        const uint64_t key = position_key(p);
        TTEntry& entry = tt[key % tt.size()];
        thc::Move ttmove{}; ttmove.Invalid();
        if (entry.key == key) {
            ttmove = entry.best;
            if (entry.depth >= depth && ply > 0) {
                int score = score_from_tt(entry.score, ply);
                if (entry.bound == EXACT || (entry.bound == LOWER && score >= beta) || (entry.bound == UPPER && score <= alpha)) return score;
            }
        }
        const bool parent_in_check = in_check(p);
        std::vector<thc::Move> moves;
        p.GenLegalMoveList(moves);
        if (moves.empty()) return parent_in_check ? -MATE + ply : 0;
        std::stable_sort(moves.begin(), moves.end(), [&](const thc::Move& a, const thc::Move& b) {
            return move_score(p, a, ttmove, ply) > move_score(p, b, ttmove, ply);
        });
        int best_score = -INF;
        thc::Move best{}; best.Invalid();
        int move_index = 0;
        for (auto m : moves) {
            const bool capture = m.capture != ' ';
            const bool promo = promotion(m);
            p.PushMove(m);
            const bool gives_check = in_check(p);
            int next_depth = depth - 1;
            const bool extend = gives_check && extensions < 2 && depth <= 10;
            if (extend) ++next_depth;
            int score;
            if (move_index == 0) {
                score = -search(p, next_depth, -beta, -alpha, ply+1, extensions + (extend ? 1 : 0));
            } else {
                int reduction = (move_index >= 4 && depth >= 3 && !capture && !promo && !gives_check && !parent_in_check) ? 1 : 0;
                score = -search(p, std::max(0, next_depth-reduction), -alpha-1, -alpha, ply+1, extensions + (extend ? 1 : 0));
                if (score > alpha && (reduction || score < beta))
                    score = -search(p, next_depth, -beta, -alpha, ply+1, extensions + (extend ? 1 : 0));
            }
            p.PopMove(m);
            if (stop.load(std::memory_order_relaxed)) return 0;
            ++move_index;
            if (score > best_score) { best_score = score; best = m; }
            if (score > alpha) {
                alpha = score;
                pv[ply][0] = m;
                for (int i = 0; i < pv_len[ply+1] && i+1 < MAX_PLY; ++i) pv[ply][i+1] = pv[ply+1][i];
                pv_len[ply] = std::min(MAX_PLY-1, pv_len[ply+1]+1);
            }
            if (alpha >= beta) {
                if (!capture && !promo && ply < MAX_PLY) {
                    if (m != killers[ply][0]) { killers[ply][1]=killers[ply][0]; killers[ply][0]=m; }
                    int& h = history[p.white ? 0 : 1][m.src][m.dst];
                    h = std::min(200000, h + depth*depth*8);
                }
                break;
            }
            if (poll_stop()) return 0;
        }
        if (entry.key == 0) ++tt_used;
        entry.key = key; entry.depth = static_cast<int8_t>(std::min(depth, 127));
        entry.score = static_cast<int16_t>(std::max(-32760, std::min(32760, score_to_tt(best_score, ply))));
        entry.bound = best_score <= original_alpha ? UPPER : best_score >= beta ? LOWER : EXACT;
        entry.best = best; entry.age = age;
        return best_score;
    }
    std::string pv_text(const thc::ChessRules& root, int len) {
        thc::ChessRules p = root;
        std::string out;
        for (int i = 0; i < len; ++i) {
            if (!pv[0][i].Valid()) break;
            out += (out.empty() ? "" : " ") + pv[0][i].TerseOut();
            thc::Move m = pv[0][i]; p.PlayMove(m);
        }
        return out;
    }
    void start_search(const thc::ChessRules& root, SearchLimits limits) {
        stop_search(); stop.store(false, std::memory_order_relaxed); ++age;
        uint16_t book_weight = 0;
        const std::string opening_move = book_move(root, book_weight);
        if (!opening_move.empty()) {
            output("info string opening book move " + opening_move + " weight " + std::to_string(book_weight) + "\n");
            output("bestmove " + opening_move + "\n");
            return;
        }
        worker = std::thread([this, root, limits]() mutable {
            board = root; nodes = 0; seldepth = 0; pv_len.fill(0);
            for (auto& row : killers) for (auto& m : row) m.Invalid();
            start_time = Clock::now(); has_deadline = false;
            int maxdepth = limits.depth > 0 ? std::min(max_depth, limits.depth) : max_depth;
            int budget = limits.movetime;
            if (budget <= 0 && !limits.infinite) {
                int remaining = board.white ? limits.wtime : limits.btime;
                int inc = board.white ? limits.winc : limits.binc;
                if (remaining >= 0) budget = std::max(40, std::min(std::max(40, remaining-move_overhead), remaining / std::max(10, limits.movestogo) + inc*3/4));
            }
            if (budget > 0 && !limits.infinite) { deadline = start_time + std::chrono::milliseconds(std::max(10, budget-move_overhead)); has_deadline = true; }
            std::string bestmove = "0000";
            int bestscore = 0;
            std::vector<thc::Move> rootmoves; board.GenLegalMoveList(rootmoves);
            if (!rootmoves.empty()) bestmove = rootmoves[0].TerseOut();
            for (int depth = 1; depth <= maxdepth && !stop.load(); ++depth) {
                seldepth = 0;
                int score = search(board, depth, -INF, INF, 0, 0);
                if (stop.load()) break;
                if (pv_len[0] > 0) { bestmove = pv[0][0].TerseOut(); bestscore = score; }
                auto elapsed = std::max<int64_t>(1, std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now()-start_time).count());
                uint64_t nps = nodes * 1000 / static_cast<uint64_t>(elapsed);
                std::ostringstream info;
                info << "info depth " << depth << " seldepth " << seldepth << " score ";
                if (std::abs(bestscore) > MATE-MAX_PLY) {
                    int mate = (MATE-std::abs(bestscore)+1)/2;
                    info << "mate " << (bestscore < 0 ? -mate : mate);
                } else info << "cp " << bestscore;
                info << " nodes " << nodes << " nps " << nps << " hashfull "
                     << std::min<size_t>(1000, 1000*tt_used/tt.size())
                     << " time " << elapsed << " pv " << pv_text(board, pv_len[0]) << "\n";
                output(info.str());
                if (std::abs(score) > MATE - 100) break;
                if (has_deadline && Clock::now() >= deadline) break;
            }
            if (limits.infinite) while (!stop.load()) std::this_thread::sleep_for(std::chrono::milliseconds(10));
            output("bestmove " + bestmove + "\n");
        });
    }
};

SearchLimits parse_go(const std::string& cmd) {
    SearchLimits limits;
    std::istringstream in(cmd); std::string token; in >> token;
    while (in >> token) {
        if (token == "depth") in >> limits.depth;
        else if (token == "movetime") in >> limits.movetime;
        else if (token == "wtime") in >> limits.wtime;
        else if (token == "btime") in >> limits.btime;
        else if (token == "winc") in >> limits.winc;
        else if (token == "binc") in >> limits.binc;
        else if (token == "movestogo") in >> limits.movestogo;
        else if (token == "infinite" || token == "ponder") limits.infinite = true;
    }
    return limits;
}

bool set_position(thc::ChessRules& board, const std::string& cmd) {
    std::istringstream in(cmd); std::string token; in >> token; in >> token;
    thc::ChessRules next;
    if (token == "startpos") {
        next.Init();
        in >> token;
    } else if (token == "fen") {
        std::string fen, part;
        while (in >> part && part != "moves") { if (!fen.empty()) fen += ' '; fen += part; }
        if (fen.empty() || !next.Forsyth(fen.c_str())) return false;
        token = part;
    } else return false;
    if (token == "moves") {
        while (in >> token) {
            thc::Move m{};
            if (!m.TerseIn(&next, token.c_str())) return false;
            next.PlayMove(m);
        }
    }
    board = next;
    return true;
}

void run_uci() {
    Engine engine;
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line == "uci") {
            output("id name Sargon Tal Fischer 64-bit 1.0\nid author RoboChess community\n"
                   "option name Hash type spin default 16 min 1 max 32\n"
                   "option name Max Depth type spin default 20 min 1 max 20\n"
                   "option name Style type combo default Tal-Fischer var Tal-Fischer var Tal var Fischer\n"
                   "option name Aggression type spin default 72 min 0 max 100\n"
                   "option name Move Overhead type spin default 40 min 0 max 500\n"
                   "option name OwnBook type check default true\n"
                   "option name Book File type string default Sargon-Tal-Fischer.bin\n"
                   "option name Book Depth type spin default 24 min 0 max 80\n"
                   "option name Book Random type check default true\n"
                   "option name Clear Hash type button\nuciok\n");
        } else if (line == "isready") output("readyok\n");
        else if (line == "ucinewgame") { engine.stop_search(); thc::ChessRules reset; engine.board = reset; engine.clear_hash(); }
        else if (line.rfind("setoption", 0) == 0) {
            engine.stop_search();
            std::istringstream in(line); std::string token; in >> token;
            std::string name, value; bool reading_value = false;
            while (in >> token) {
                if (token == "name") {
                    name.clear(); reading_value = false;
                    while (in >> token && token != "value") { if (!name.empty()) name += ' '; name += token; }
                    if (token == "value") reading_value = true;
                } else if (reading_value) { if (!value.empty()) value += ' '; value += token; }
            }
            if (name == "Hash") engine.resize_hash(std::atoi(value.c_str()));
            else if (name == "Max Depth") engine.max_depth=std::max(1,std::min(MAX_DEPTH,std::atoi(value.c_str())));
            else if (name == "Style" && (value == "Tal-Fischer" || value == "Tal" || value == "Fischer")) engine.style=value;
            else if (name == "Aggression") engine.aggression=std::max(0,std::min(100,std::atoi(value.c_str())));
            else if (name == "Move Overhead") engine.move_overhead=std::max(0,std::min(500,std::atoi(value.c_str())));
            else if (name == "OwnBook") engine.own_book=(value == "true" || value == "1");
            else if (name == "Book File") { engine.book_file=value; engine.load_book(); }
            else if (name == "Book Depth") engine.book_depth=std::max(0,std::min(80,std::atoi(value.c_str())));
            else if (name == "Book Random") engine.book_random=(value == "true" || value == "1");
            else if (name == "Clear Hash") engine.clear_hash();
        } else if (line.rfind("position", 0) == 0) {
            engine.stop_search();
            if (!set_position(engine.board, line)) output("info string invalid position command\n");
        } else if (line.rfind("go", 0) == 0) {
            engine.start_search(engine.board, parse_go(line));
        } else if (line == "stop") engine.stop_search();
        else if (line == "quit") { engine.stop_search(); break; }
        else if (line == "debug on" || line == "debug off") { }
    }
}
} // namespace

int main() { run_uci(); return 0; }
