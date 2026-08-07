#ifndef TENSOR_HPP
#define TENSOR_HPP

#include <cstddef>
#include <initializer_list>
#include <vector>

using tensor_t = float;

enum class DeviceType {
    CPU,
    CUDA,
    NPU
};

class Tensor {
public:
    Tensor();
    explicit Tensor(const std::vector<std::size_t>& shape,
                    DeviceType device = DeviceType::CPU);
    Tensor(std::initializer_list<std::size_t> shape,
           DeviceType device = DeviceType::CPU);
    Tensor(std::size_t dim, const std::size_t* shape,
           DeviceType device = DeviceType::CPU);

    Tensor(const Tensor&) = default;
    Tensor(Tensor&&) noexcept = default;
    Tensor& operator=(const Tensor&) = default;
    Tensor& operator=(Tensor&&) noexcept = default;
    ~Tensor() = default;

    /** @brief Get the rank (number of dimensions) of the tensor. */
    std::size_t rank() const noexcept { return shape_.size(); }
    /** @brief Get the shape of the tensor. */
    const std::vector<std::size_t>& shape() const noexcept { return shape_; }
    /** @brief Get the strides of the tensor. */
    const std::vector<std::size_t>& strides() const noexcept { return strides_; }
    /** @brief Get the total number of elements in the tensor. */
    std::size_t size() const noexcept { return data_.size(); }
    /** @brief Get the device type of the tensor. */
    DeviceType device() const noexcept { return device_; }

    tensor_t* data() noexcept { return data_.data(); }
    const tensor_t* data() const noexcept { return data_.data(); }

    tensor_t& at(const std::vector<std::size_t>& indices);
    const tensor_t& at(const std::vector<std::size_t>& indices) const;
    tensor_t& at(std::initializer_list<std::size_t> indices);
    const tensor_t& at(std::initializer_list<std::size_t> indices) const;

    void reshape(const std::vector<std::size_t>& new_shape);
    void reshape(std::initializer_list<std::size_t> new_shape);
    void fill(tensor_t value) noexcept;
    void zero() noexcept { fill(0.0f); }

    tensor_t sum() const;
    tensor_t mean() const;
    tensor_t max() const;

    Tensor transpose() const;
    Tensor matmul(const Tensor& other) const;

    Tensor operator+(const Tensor& other) const;
    Tensor operator-(const Tensor& other) const;
    Tensor operator*(const Tensor& other) const;
    Tensor operator/(const Tensor& other) const;
    Tensor operator*(tensor_t scalar) const;

    static Tensor zeros(const std::vector<std::size_t>& shape,
                        DeviceType device = DeviceType::CPU);
    static Tensor ones(const std::vector<std::size_t>& shape,
                       DeviceType device = DeviceType::CPU);

private:
    std::vector<std::size_t> shape_;
    std::vector<std::size_t> strides_;
    std::vector<tensor_t> data_;
    DeviceType device_;

    void initialize(const std::vector<std::size_t>& shape, DeviceType device);
    void ensure_cpu(const char* operation) const;
    std::size_t offset(const std::vector<std::size_t>& indices) const;
    static std::size_t element_count(const std::vector<std::size_t>& shape);
    static std::vector<std::size_t> make_strides(const std::vector<std::size_t>& shape);
};

#endif
