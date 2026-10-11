// Exercise the actual private instance type through the existing test friend.
#include "Parser.h"
#include <cassert>
#include <iostream>
#include <type_traits>
struct SourceTranslationTestAccess {
    static void run() {
        using Instance = Parser::LambdaInstance;
        static_assert(std::is_same<decltype(Instance::syntax),
            std::shared_ptr<const nift::detail::LambdaSyntaxMetadata>>::value,
            "Published syntax must be immutable");
        for (int order = 0; order != 6; ++order) {
            auto construction = std::make_shared<nift::detail::LambdaSyntaxMetadata>();
            construction->params = {"x"}; construction->body = "x+1";
            construction->variadic_param = "rest"; construction->async = true;
            construction->block = true; construction->body_offset = 17;
            std::shared_ptr<const nift::detail::LambdaSyntaxMetadata> descriptor = construction;
            construction.reset();
            std::weak_ptr<const nift::detail::LambdaSyntaxMetadata> lifetime = descriptor;
            auto original = std::make_shared<Instance>();
            original->syntax = descriptor; original->async = true;
            original->source_path = "original.f";
            auto a = std::make_shared<Instance>(*original);
            auto b = std::make_shared<Instance>(*original);
            a->async = false; a->source_path = "clone.f";
            assert(b->async && original->async);
            assert(b->source_path == "original.f" && original->source_path == "original.f");
            assert(a->syntax == b->syntax && b->syntax == original->syntax);
            assert(descriptor->async && descriptor->block && descriptor->body_offset == 17);
            assert(descriptor->params == std::vector<std::string>{"x"});
            assert(descriptor->body == "x+1" && descriptor->variadic_param == "rest");
            descriptor.reset();
            std::shared_ptr<Instance> consumers[] = {original, a, b};
            original.reset(); a.reset(); b.reset();
            const int orders[6][3] = {{0,1,2},{0,2,1},{1,0,2},{1,2,0},{2,0,1},{2,1,0}};
            for (int i = 0; i != 3; ++i) {
                assert(!lifetime.expired());
                assert(consumers[orders[order][i]]->syntax->body == "x+1");
                consumers[orders[order][i]].reset();
            }
            assert(lifetime.expired());
        }
    }
};
int main() {
    SourceTranslationTestAccess::run();
#if defined(_MSVC_STL_VERSION)
    std::cout << "MSVC STL " << _MSVC_STL_VERSION;
#elif defined(_LIBCPP_VERSION)
    std::cout << "libc++ " << _LIBCPP_VERSION;
#elif defined(__GLIBCXX__)
    std::cout << "libstdc++ " << __GLIBCXX__;
#else
#error Unknown STL: certification requires an identified implementation
#endif
    std::cout << ": PASS actual LambdaInstance clone/const syntax/all six destruction orders\n";
}
