#pragma once
#include <string>
#include <vector>
#include <cstddef>
namespace nift { namespace detail {
// Published through shared_ptr<const>; contains no captures, origin, or identity.
struct LambdaSyntaxMetadata {
    std::vector<std::string> params;
    std::string variadic_param, body;
    bool block = false, async = false;
    std::size_t body_offset = 0;
};
}}
