#pragma once

#include <cstdint>
#include <istream>
#include <ostream>
#include "thc.h"

namespace sargon_book {
constexpr char MAGIC[8] = {'S', 'A', 'R', 'G', 'O', 'N', 'B', '1'};
constexpr uint32_t VERSION = 1;
constexpr uint32_t MAX_RECORDS = 5000000;

inline uint64_t mix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

// Sargon's portable book key ignores the 50-move counter but includes side,
// castling rights and a legal en-passant target.
inline uint64_t position_key(thc::ChessPosition& p) {
    uint64_t key = p.Hash64Calculate();
    const unsigned rights = (p.wking ? 1u : 0u) | (p.wqueen ? 2u : 0u) |
                            (p.bking ? 4u : 0u) | (p.bqueen ? 8u : 0u);
    key ^= mix64(0x534152474f4eULL + rights + (p.white ? 0x100u : 0u));
    if (p.enpassant_target != thc::SQUARE_INVALID)
        key ^= mix64(0x45504ULL + static_cast<unsigned>(p.enpassant_target));
    return key;
}

inline void write_u16(std::ostream& out, uint16_t value) {
    out.put(static_cast<char>(value & 0xff));
    out.put(static_cast<char>((value >> 8) & 0xff));
}
inline void write_u32(std::ostream& out, uint32_t value) {
    for (int i = 0; i < 4; ++i) out.put(static_cast<char>((value >> (8 * i)) & 0xff));
}
inline void write_u64(std::ostream& out, uint64_t value) {
    for (int i = 0; i < 8; ++i) out.put(static_cast<char>((value >> (8 * i)) & 0xff));
}
inline bool read_u16(std::istream& in, uint16_t& value) {
    unsigned char b[2];
    if (!in.read(reinterpret_cast<char*>(b), 2)) return false;
    value = static_cast<uint16_t>(b[0] | (static_cast<uint16_t>(b[1]) << 8));
    return true;
}
inline bool read_u32(std::istream& in, uint32_t& value) {
    unsigned char b[4];
    if (!in.read(reinterpret_cast<char*>(b), 4)) return false;
    value = 0;
    for (int i = 0; i < 4; ++i) value |= static_cast<uint32_t>(b[i]) << (8 * i);
    return true;
}
inline bool read_u64(std::istream& in, uint64_t& value) {
    unsigned char b[8];
    if (!in.read(reinterpret_cast<char*>(b), 8)) return false;
    value = 0;
    for (int i = 0; i < 8; ++i) value |= static_cast<uint64_t>(b[i]) << (8 * i);
    return true;
}
} // namespace sargon_book
