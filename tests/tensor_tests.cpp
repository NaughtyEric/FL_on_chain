#include "tensor.hpp"

#include <cassert>
#include <cmath>
#include <functional>
#include <iostream>
#include <stdexcept>

namespace {

void expect_throw(const std::function<void()>& operation) {
    bool thrown = false;
    try { operation(); } catch (const std::exception&) { thrown = true; }
    assert(thrown);
}

void expect_close(float actual, float expected) {
    assert(std::fabs(actual - expected) < 1e-5f);
}

} // namespace

int main() {
    Tensor tensor({2, 3});
    assert(tensor.rank() == 2);
    assert(tensor.size() == 6);
    tensor.fill(2.0f);
    tensor.at({1, 2}) = 7.0f;
    expect_close(tensor.at({1, 2}), 7.0f);
    expect_throw([&] { tensor.at({2, 0}); });
    expect_throw([&] { tensor.at({0}); });

    tensor.reshape({3, 2});
    assert(tensor.strides()[0] == 2);
    expect_close(tensor.at({2, 1}), 7.0f);
    expect_throw([&] { tensor.reshape({4, 2}); });

    Tensor copy = tensor;
    copy.at({0, 0}) = 99.0f;
    assert(tensor.at({0, 0}) != copy.at({0, 0}));

    Tensor left({2, 3});
    Tensor right({2, 3});
    for (std::size_t i = 0; i < 6; ++i) {
        left.data()[i] = static_cast<float>(i);
        right.data()[i] = 1.0f;
    }
    Tensor added = left + right;
    expect_close(added.at({1, 2}), 6.0f);
    expect_close(left.sum(), 15.0f);
    expect_close(left.mean(), 2.5f);
    expect_close(left.max(), 5.0f);

    Tensor matrix_a({2, 3});
    Tensor matrix_b({3, 2});
    for (std::size_t i = 0; i < matrix_a.size(); ++i) matrix_a.data()[i] = static_cast<float>(i + 1);
    for (std::size_t i = 0; i < matrix_b.size(); ++i) matrix_b.data()[i] = static_cast<float>(i + 1);
    Tensor product = matrix_a.matmul(matrix_b);
    expect_close(product.at({0, 0}), 22.0f);
    expect_close(product.at({1, 1}), 64.0f);

    Tensor transposed = matrix_a.transpose();
    assert(transposed.shape() == std::vector<std::size_t>({3, 2}));
    expect_close(transposed.at({2, 1}), 6.0f);

    Tensor ones = Tensor::ones({2, 2});
    expect_close(ones.sum(), 4.0f);
    expect_throw([] { Tensor({2, 2}, DeviceType::NPU); });

    std::cout << "All tensor tests passed\n";
    return 0;
}
