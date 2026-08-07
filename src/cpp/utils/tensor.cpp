#include "tensor.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>

namespace {

void validate_device(DeviceType device, const char* operation) {
    if (device != DeviceType::CPU) {
        throw std::runtime_error(std::string(operation) +
                                 ": requested device backend is not implemented");
    }
}

tensor_t apply_binary(tensor_t lhs, tensor_t rhs, char operation) {
    switch (operation) {
        case '+': return lhs + rhs;
        case '-': return lhs - rhs;
        case '*': return lhs * rhs;
        case '/':
            if (rhs == 0.0f) {
                throw std::domain_error("Tensor division by zero");
            }
            return lhs / rhs;
        default: throw std::logic_error("Unknown tensor binary operation");
    }
}

} // namespace

Tensor::Tensor() : device_(DeviceType::CPU) {}

Tensor::Tensor(const std::vector<std::size_t>& shape, DeviceType device) {
    initialize(shape, device);
}

Tensor::Tensor(std::initializer_list<std::size_t> shape, DeviceType device) {
    initialize(std::vector<std::size_t>(shape), device);
}

Tensor::Tensor(std::size_t dim, const std::size_t* shape, DeviceType device) {
    if (dim != 0 && shape == nullptr) {
        throw std::invalid_argument("Tensor shape pointer must not be null");
    }
    initialize(std::vector<std::size_t>(shape, shape + dim), device);
}

void Tensor::initialize(const std::vector<std::size_t>& shape, DeviceType device) {
    validate_device(device, "Tensor construction");
    shape_ = shape;
    strides_ = make_strides(shape_);
    data_.assign(element_count(shape_), 0.0f);
    device_ = device;
}

std::size_t Tensor::element_count(const std::vector<std::size_t>& shape) {
    if (shape.empty()) {
        return 0;
    }

    std::size_t count = 1;
    for (std::size_t dimension : shape) {
        if (dimension == 0 || count > std::numeric_limits<std::size_t>::max() / dimension) {
            throw std::invalid_argument("Tensor dimensions must be non-zero and fit in memory");
        }
        count *= dimension;
    }
    return count;
}

std::vector<std::size_t> Tensor::make_strides(const std::vector<std::size_t>& shape) {
    std::vector<std::size_t> result(shape.size(), 1);
    for (std::size_t i = shape.size(); i > 1; --i) {
        result[i - 2] = result[i - 1] * shape[i - 1];
    }
    return result;
}

void Tensor::ensure_cpu(const char* operation) const {
    validate_device(device_, operation);
}

std::size_t Tensor::offset(const std::vector<std::size_t>& indices) const {
    if (indices.size() != shape_.size()) {
        throw std::out_of_range("Tensor index rank does not match tensor rank");
    }

    std::size_t result = 0;
    for (std::size_t i = 0; i < indices.size(); ++i) {
        if (indices[i] >= shape_[i]) {
            throw std::out_of_range("Tensor index is out of bounds");
        }
        result += indices[i] * strides_[i];
    }
    return result;
}

tensor_t& Tensor::at(const std::vector<std::size_t>& indices) {
    ensure_cpu("Tensor indexing");
    return data_[offset(indices)];
}

const tensor_t& Tensor::at(const std::vector<std::size_t>& indices) const {
    ensure_cpu("Tensor indexing");
    return data_[offset(indices)];
}

tensor_t& Tensor::at(std::initializer_list<std::size_t> indices) {
    return at(std::vector<std::size_t>(indices));
}

const tensor_t& Tensor::at(std::initializer_list<std::size_t> indices) const {
    return at(std::vector<std::size_t>(indices));
}

void Tensor::reshape(const std::vector<std::size_t>& new_shape) {
    ensure_cpu("Tensor reshape");
    if (element_count(new_shape) != data_.size()) {
        throw std::invalid_argument("Reshape must preserve the number of elements");
    }
    shape_ = new_shape;
    strides_ = make_strides(shape_);
}

void Tensor::reshape(std::initializer_list<std::size_t> new_shape) {
    reshape(std::vector<std::size_t>(new_shape));
}

void Tensor::fill(tensor_t value) noexcept {
    std::fill(data_.begin(), data_.end(), value);
}

tensor_t Tensor::sum() const {
    ensure_cpu("Tensor sum");
    return std::accumulate(data_.begin(), data_.end(), 0.0f);
}

tensor_t Tensor::mean() const {
    ensure_cpu("Tensor mean");
    if (data_.empty()) {
        throw std::domain_error("Mean of an empty tensor");
    }
    return sum() / static_cast<tensor_t>(data_.size());
}

tensor_t Tensor::max() const {
    ensure_cpu("Tensor max");
    if (data_.empty()) {
        throw std::domain_error("Maximum of an empty tensor");
    }
    return *std::max_element(data_.begin(), data_.end());
}

Tensor Tensor::transpose() const {
    ensure_cpu("Tensor transpose");
    if (rank() != 2) {
        throw std::invalid_argument("Transpose currently requires a rank-2 tensor");
    }

    Tensor result({shape_[1], shape_[0]});
    for (std::size_t row = 0; row < shape_[0]; ++row) {
        for (std::size_t column = 0; column < shape_[1]; ++column) {
            result.at({column, row}) = at({row, column});
        }
    }
    return result;
}

Tensor Tensor::matmul(const Tensor& other) const {
    ensure_cpu("Tensor matrix multiplication");
    other.ensure_cpu("Tensor matrix multiplication");
    if (rank() != 2 || other.rank() != 2 || shape_[1] != other.shape_[0]) {
        throw std::invalid_argument("Matrix multiplication requires compatible rank-2 tensors");
    }

    Tensor result({shape_[0], other.shape_[1]});
    for (std::size_t row = 0; row < shape_[0]; ++row) {
        for (std::size_t column = 0; column < other.shape_[1]; ++column) {
            tensor_t value = 0.0f;
            for (std::size_t inner = 0; inner < shape_[1]; ++inner) {
                value += at({row, inner}) * other.at({inner, column});
            }
            result.at({row, column}) = value;
        }
    }
    return result;
}

Tensor Tensor::operator+(const Tensor& other) const {
    ensure_cpu("Tensor addition");
    other.ensure_cpu("Tensor addition");
    if (shape_ != other.shape_) throw std::invalid_argument("Tensor shapes must match");
    Tensor result(shape_);
    for (std::size_t i = 0; i < data_.size(); ++i) result.data_[i] = apply_binary(data_[i], other.data_[i], '+');
    return result;
}

Tensor Tensor::operator-(const Tensor& other) const {
    ensure_cpu("Tensor subtraction");
    other.ensure_cpu("Tensor subtraction");
    if (shape_ != other.shape_) throw std::invalid_argument("Tensor shapes must match");
    Tensor result(shape_);
    for (std::size_t i = 0; i < data_.size(); ++i) result.data_[i] = apply_binary(data_[i], other.data_[i], '-');
    return result;
}

Tensor Tensor::operator*(const Tensor& other) const {
    ensure_cpu("Tensor multiplication");
    other.ensure_cpu("Tensor multiplication");
    if (shape_ != other.shape_) throw std::invalid_argument("Tensor shapes must match");
    Tensor result(shape_);
    for (std::size_t i = 0; i < data_.size(); ++i) result.data_[i] = apply_binary(data_[i], other.data_[i], '*');
    return result;
}

Tensor Tensor::operator/(const Tensor& other) const {
    ensure_cpu("Tensor division");
    other.ensure_cpu("Tensor division");
    if (shape_ != other.shape_) throw std::invalid_argument("Tensor shapes must match");
    Tensor result(shape_);
    for (std::size_t i = 0; i < data_.size(); ++i) result.data_[i] = apply_binary(data_[i], other.data_[i], '/');
    return result;
}

Tensor Tensor::operator*(tensor_t scalar) const {
    ensure_cpu("Tensor scalar multiplication");
    Tensor result(shape_);
    for (std::size_t i = 0; i < data_.size(); ++i) result.data_[i] = data_[i] * scalar;
    return result;
}

Tensor Tensor::zeros(const std::vector<std::size_t>& shape, DeviceType device) {
    return Tensor(shape, device);
}

Tensor Tensor::ones(const std::vector<std::size_t>& shape, DeviceType device) {
    Tensor result(shape, device);
    result.fill(1.0f);
    return result;
}
