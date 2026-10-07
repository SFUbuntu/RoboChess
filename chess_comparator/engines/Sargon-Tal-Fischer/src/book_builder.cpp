#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>
#include "book_format.h"

namespace {
using KeyMove = std::pair<uint64_t, std::string>;

std::string tag_value(const std::string& line, const std::string& tag) {
    const std::string prefix = "[" + tag + " \"";
    if (line.rfind(prefix, 0) != 0) return {};
    const auto end = line.find('"', prefix.size());
    return end == std::string::npos ? std::string{} : line.substr(prefix.size(), end-prefix.size());
}

void process_token(std::string token, thc::ChessRules& board, int& ply,
                   int max_ply, std::map<KeyMove, uint64_t>& counts,
                   uint64_t& games, bool& bad_game, uint64_t& rejected) {
    if (token.empty() || token[0] == '$') return;
    if (token == "1-0" || token == "0-1" || token == "1/2-1/2" || token == "*") {
        if (ply > 0) ++games;
        thc::ChessRules fresh; board = fresh; ply = 0; bad_game = false;
        return;
    }
    // Remove PGN move numbers, including attached forms such as "12.Nf3".
    size_t i = 0;
    while (i < token.size() && (std::isdigit(static_cast<unsigned char>(token[i])) || token[i] == '.')) ++i;
    if (i) token.erase(0, i);
    if (token.empty() || token == "e.p." || token == "ep") return;
    if (bad_game) return;
    if (token.rfind("[", 0) == 0) return;
    if (token == "0-0") token = "O-O";
    else if (token == "0-0-0") token = "O-O-O";

    thc::Move move{};
    if (!move.NaturalIn(&board, token.c_str())) {
        ++rejected;
        bad_game = true;
        return;
    }
    if (ply < max_ply) {
        const std::string uci = move.TerseOut();
        ++counts[{sargon_book::position_key(board), uci}];
    }
    board.PlayMove(move);
    ++ply;
}

void tokenize_movetext(const std::string& line, thc::ChessRules& board,
                       int& ply, int max_ply, std::map<KeyMove, uint64_t>& counts,
                       uint64_t& games, bool& bad_game, uint64_t& rejected,
                       int& variations, bool& brace_comment, bool& semicolon_comment) {
    std::string token;
    auto flush = [&] {
        if (!token.empty()) process_token(token, board, ply, max_ply, counts, games, bad_game, rejected);
        token.clear();
    };
    for (char ch : line) {
        if (semicolon_comment) {
            if (ch == '\n' || ch == '\r') semicolon_comment = false;
            continue;
        }
        if (brace_comment) {
            if (ch == '}') brace_comment = false;
            continue;
        }
        if (ch == '{') { flush(); brace_comment = true; continue; }
        if (ch == ';') { flush(); semicolon_comment = true; continue; }
        if (ch == '(') { flush(); ++variations; continue; }
        if (ch == ')' && variations > 0) { flush(); --variations; continue; }
        if (variations > 0) continue;
        if (std::isspace(static_cast<unsigned char>(ch))) flush();
        else token.push_back(ch);
    }
    flush();
}

} // namespace

int main(int argc, char** argv) {
    if (argc < 3 || argc > 4) {
        std::cerr << "Usage: SargonBookBuilder INPUT.pgn OUTPUT.bin [max_plies]\n";
        return 2;
    }
    const int max_ply = argc == 4 ? std::max(1, std::min(80, std::atoi(argv[3]))) : 24;
    std::ifstream pgn(argv[1]);
    if (!pgn) { std::cerr << "Cannot open PGN: " << argv[1] << "\n"; return 2; }

    std::map<KeyMove, uint64_t> counts;
    thc::ChessRules board;
    int ply = 0, variations = 0;
    uint64_t games = 0, rejected = 0;
    bool bad_game = false, brace_comment = false, semicolon_comment = false;
    std::string line;
    while (std::getline(pgn, line)) {
        if (line.rfind("[Event ", 0) == 0) {
            if (ply > 0) ++games;
            thc::ChessRules fresh; board = fresh; ply = 0; bad_game = false; variations = 0;
            continue;
        }
        if (line.rfind("[FEN \"", 0) == 0) {
            const std::string fen = tag_value(line, "FEN");
            if (!fen.empty() && !board.Forsyth(fen.c_str())) {
                ++rejected; bad_game = true;
            }
            continue;
        }
        if (!line.empty() && line[0] == '[') continue;
        tokenize_movetext(line, board, ply, max_ply, counts, games, bad_game,
                          rejected, variations, brace_comment, semicolon_comment);
        semicolon_comment = false; // getline already removed the newline.
    }
    if (ply > 0) ++games;
    if (counts.empty()) { std::cerr << "No valid opening moves were found. Rejected tokens: " << rejected << "\n"; return 1; }

    std::ofstream out(argv[2], std::ios::binary | std::ios::trunc);
    if (!out) { std::cerr << "Cannot create book: " << argv[2] << "\n"; return 2; }
    out.write(sargon_book::MAGIC, sizeof(sargon_book::MAGIC));
    sargon_book::write_u32(out, sargon_book::VERSION);
    sargon_book::write_u32(out, static_cast<uint32_t>(counts.size()));
    for (const auto& item : counts) {
        sargon_book::write_u64(out, item.first.first);
        char move[6]{};
        const std::string& uci = item.first.second;
        std::copy_n(uci.c_str(), std::min<size_t>(5, uci.size()), move);
        out.write(move, sizeof(move));
        const uint16_t weight = static_cast<uint16_t>(std::min<uint64_t>(65535, item.second));
        sargon_book::write_u16(out, weight);
    }
    if (!out) { std::cerr << "Failed while writing book data.\n"; return 2; }
    std::cout << "Games read: " << games << "\nBook moves: " << counts.size()
              << "\nMaximum plies: " << max_ply << "\nRejected moves/FENs: " << rejected
              << "\nCreated: " << argv[2] << "\n";
    return 0;
}
