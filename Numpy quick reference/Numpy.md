# Numpy

# 📐 NumPy x 线性代数速查表 (Cheatsheet)

---

## 1. 🧱 建立矩阵 (Definitions)

把数学课本上的符号“翻译”成代码。

---

## 2. ⚡️ 核心运算 (Operations)

⚠️ **注意：** 必须区分 **矩阵乘法** 和 **普通乘法**。

---

## 3. 🧮 线性代数工具箱 (`np.linalg`)

这是线代学习的“重型武器”，位于 `numpy.linalg` 模块下。

### 常用函数速查

```python
import numpy as np

# 假设 A 是一个方阵，b 是向量
A = np.array([[1, 2], [3, 4]])
b = np.array([5, 6])

# 1. 求逆矩阵 (Inverse) -> A^(-1)
A_inv = np.linalg.inv(A)

# 2. 求行列式 (Determinant) -> |A|
det = np.linalg.det(A)

# 3. 解线性方程组 (Solve) -> Ax = b
x = np.linalg.solve(A, b)

# 4. 求特征值与特征向量 (Eigenvalues) -> Av = λv
vals, vecs = np.linalg.eig(A)
# vals: 特征值数组
# vecs: 特征向量矩阵 (每一列是一个特征向量)

# 5. 求秩 (Rank)
rank = np.linalg.matrix_rank(A)

# 6. 求范数/模长 (Norm) -> ||v||
length = np.linalg.norm(b)
```

