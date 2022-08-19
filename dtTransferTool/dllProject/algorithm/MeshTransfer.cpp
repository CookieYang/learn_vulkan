#include "MeshTransfer.h"
#include <fstream>
#include "ParameterConfig.h"

	typedef MeshTransfer::real real;
	typedef MeshTransfer::Float3 Float3;
	typedef MeshTransfer::Int3 Int3;
	typedef MeshTransfer::Int4 Int4;
	typedef MeshTransfer::Mat3f Mat3f;

	void Dump(const MeshTransfer::SpMat& A, std::string name)
	{
		FILE* pFile = fopen(name.c_str(), "w");
		for (int c = 0; c < A.cols(); c++)
		{
			const int colBegin = A.outerIndexPtr()[c];
			const int colEnd = A.outerIndexPtr()[c + 1];
			for (int i = colBegin; i < colEnd; i++)
			{
				const int r = A.innerIndexPtr()[i];
				MeshTransfer::real val = A.valuePtr()[i];
				fprintf(pFile, "%d %d %lf\n", r, c, val);
			}
		}
		fclose(pFile);
	}

	void Dump(const MeshTransfer::Vec& A, std::string name)
	{
		FILE* pFile = fopen(name.c_str(), "w");
		for (int c = 0; c < A.size(); c++)
		{
			MeshTransfer::real val = A[c];
			fprintf(pFile, "%lf\n", val);
		}
		fclose(pFile);
	}

	template <class T>
	static bool hasIllegalData(const T* data, int n)
	{
		for (int i = 0; i < n; i++)
		{
			if (std::isinf(data[i]) || std::isnan(data[i]))
				return true;
		}
		return false;
	}

	bool hasIllegalTriangle(const Int3* pTris, int n)
	{
		for (int i = 0; i < n; i++)
		{
			const Int3& t = pTris[i];
			if (t[0] < 0 || t[1] < 0 || t[2] < 0)
				return true;
			if (t[0] == t[1] || t[0] == t[2] || t[1] == t[2])
				return true;
		}
		return false;
	}

	const char* MeshTransfer::getErrString()const
	{
		return m_errStr.c_str();
	}

	int MeshTransfer::init(int nTriangles, const Int3* pTriangles, int nVertices,
		const Float3* pSrcVertices0, const Float3* pTarVertices0,
		const std::vector<int>& fixVertIds, const std::vector<Int2>& vertPairs)
	{
		clear();
		if (hasIllegalData((const float*)pSrcVertices0, nVertices * 3))
		{
			m_errStr = "nan or inf in input pSrcVertices0";
			return -1;
		}
		if (hasIllegalData((const float*)pTarVertices0, nVertices * 3))
		{
			m_errStr = "nan or inf in input pTarVertices0";
			return -1;
		}
		if (hasIllegalTriangle(pTriangles, nTriangles))
		{
			m_errStr = "illegal or trivial triangles in pTriangles!";
			return -2;
		}

		m_srcVerts0.resize(nVertices);
		memcpy(m_srcVerts0.data(), pSrcVertices0, nVertices * sizeof(Float3));

		m_tarVerts0.resize(nVertices);
		memcpy(m_tarVerts0.data(), pTarVertices0, nVertices * sizeof(Float3));

		m_facesTri.resize(nTriangles);
		for (int i = 0; i < nTriangles; i++)
			m_facesTri[i] = pTriangles[i];

		// precomputation
		m_vertPairs = vertPairs;
		findAnchorPoints(fixVertIds);
		setup_ancorMat();
		setup_RegularizationMat();
		setup_pairMat();
		setup_E1Mat(m_tarVerts0);
		setup_RegularizationRhs(m_tarVerts0);
		setup_ancorRhs(m_tarVerts0);
		setup_pairRhs(m_tarVerts0);

		if (hasIllegalData(m_E1Mat.valuePtr(), (int)m_E1Mat.nonZeros()))
		{
			m_errStr = "nan or inf in E1Mat!";
			return -3;
		}

		const real w_anchor = real(MeshTransferParameter::Transfer_Weight_Anchor / (1e-3f + m_ancorMat.rows()));
		const real w_reg = real(MeshTransferParameter::Transfer_Weight_Regularization / (1e-3f + m_regAtA.rows()));
		const real w1 = real(MeshTransferParameter::Transfer_Weight_Correspond / (1e-3f + m_E1Mat.rows()));
		const real w_pair = real(MeshTransferParameter::Transfer_Weight_Pair / (1e-3f + m_E1Mat.rows()));

		m_ancorMatT = m_ancorMat.transpose();
		m_E1MatT = m_E1Mat.transpose();
		m_E1MatT *= w1;

		m_AtA = m_E1MatT * m_E1Mat + m_ancorMatT * m_ancorMat * w_anchor + m_regAtA * w_reg;
		if (!m_vertPairs.empty())
			m_AtA += m_pairMatT * m_pairMat * w_pair;
		m_anchorRegSumAtb = m_ancorMatT * m_ancorRhs * w_anchor + m_regAtb * w_reg;
		if (!m_vertPairs.empty())
			m_anchorRegSumAtb += m_pairMatT * m_pairRhs * w_pair;
		m_solver.compute(m_AtA);

		m_bInit = true;
		m_shouldAnalysisTopology = true;
		return 1;
	}

	int MeshTransfer::transfer(const std::vector<Float3>& srcVertsDeformed, std::vector<Float3>& tarVertsDeformed)
	{
		if (!m_bInit)
		{
			m_errStr = "not initialized when calling transfer()";
			return -4;
		}
		if (srcVertsDeformed.size() != m_srcVerts0.size())
		{
			m_errStr = "transfer: vertex size not matched!";
			return -5;
		}
		if (hasIllegalData((const float*)srcVertsDeformed.data(), (int)srcVertsDeformed.size() * 3))
		{
			m_errStr = "nan or inf in srcVertsDeformed!";
			return -6;
		}

		// computing all energy matrices
		setup_E1Rhs(srcVertsDeformed);

		//// ldp debug
		//Dump(m_E1Mat, "E:/cml/TensorVisualizeUI/bin/test/matG1_ref.txt");
		//Dump(m_E1Rhs, "E:/cml/TensorVisualizeUI/bin/test/rhsG1_ref.txt");
		//printf("%d %d %d\n", m_E1Mat.rows(), m_E1Mat.cols(), m_E1Mat.nonZeros());
		//// end debug

		// sum all the energy terms
		m_Atb = m_E1MatT * m_E1Rhs;
		m_Atb += m_anchorRegSumAtb;

		// solve
		m_x = m_solver.solve(m_Atb);

		// return the value
		vertex_vec_to_point(m_x, tarVertsDeformed);

		if (hasIllegalData((const float*)tarVertsDeformed.data(), (int)tarVertsDeformed.size() * 3))
		{
			m_errStr = "finished transfer, but nan or inf in tarVertsDeformed!";
			return -7;
		}
		return 1;
	}

	void MeshTransfer::clear()
	{
		m_bInit = false;
		m_shouldAnalysisTopology = false;
		m_facesTri.clear();
		m_anchors.clear();
		m_srcVerts0.clear();
	}

	void MeshTransfer::findAnchorPoints(const std::vector<int>& fixVertIds)
	{
		m_anchors.clear();
		if (fixVertIds.empty())
			m_anchors.push_back(0);
		else
			m_anchors = fixVertIds;
	}

	void MeshTransfer::vertex_vec_to_point(const Vec& x, std::vector<Float3>& verts)const
	{
		verts.resize(m_srcVerts0.size());
		for (int i = 0; i < verts.size(); i++)
			for (int k = 0; k < 3; k++)
				verts[i][k] = (float)x[k*(x.size() / 3) + i];
	}

	void MeshTransfer::vertex_point_to_vec(Vec& x, const std::vector<Float3>& verts, const std::vector<Int3>& faces)const
	{
		int nTotalVerts = (int)verts.size() + (int)faces.size();
		if (x.size() != nTotalVerts)
			x.resize(nTotalVerts * 3);

		x.setZero();
		for (int i = 0; i < verts.size(); i++)
			for (int k = 0; k < 3; k++)
				x[k*nTotalVerts + i] = verts[i][k];

		for (int i = 0; i < faces.size(); i++)
		{
			int row = (int)verts.size() + i;
			const Int3& f = faces[i];
			Float3 v = verts[f[0]] + (verts[f[1]] - verts[f[0]]).cross(verts[f[2]] - verts[f[0]]).normalized();
			for (int k = 0; k < 3; k++)
				x[k*nTotalVerts + row] = v[k];
		}
	}

	inline void fill4VertsOfFace(int id_f, const std::vector<Int3>& faces, const std::vector<Float3>& verts, int *id_v, Float3* v)
	{
		Int3 f = faces[id_f];
		int k = 0;
		for (int k = 0; k < 3; k++)
		{
			id_v[k] = f[k];
			v[k] = verts[id_v[k]];
		}
		Float3 tmp1 = v[1] - v[0];
		Float3 tmp2 = v[2] - v[0];
		Float3 r = Float3(tmp1[1]*tmp2[2] - tmp2[1]*tmp1[2], 0 - (tmp1[0]*tmp2[2]-tmp2[0]*tmp1[2]), tmp1[0]*tmp2[1]-tmp2[0]*tmp1[1]);
		float s = sqrt(r[0]*r[0] + r[1]*r[1] +r[2]*r[2]);
		v[3] = v[0] + Float3(r[0]/s, r[1]/s, r[2]/s);
		id_v[3] = (int)verts.size() + id_f;
	}

	inline Mat3f getV(Float3* v)
	{
		Mat3f V;
		for (int y = 0; y < 3; y++)
			for (int x = 0; x < 3; x++)
				V(y, x) = v[x + 1][y] - v[0][y];
		return V;
	}

	inline void getMatrix_namedby_T(Float3* v, Eigen::Matrix<real, 3, 4>& A)
	{
		Mat3f V = getV(v).inverse();

		// The matrix T is in block diag style:
		// | A 0 0 |
		// | 0 A 0 |
		// | 0 0 A |
		// where each A is a 3x4 matrix
		A(0, 0) = -V(0, 0) - V(1, 0) - V(2, 0);
		A(0, 1) = V(0, 0);
		A(0, 2) = V(1, 0);
		A(0, 3) = V(2, 0);
		A(1, 0) = -V(0, 1) - V(1, 1) - V(2, 1);
		A(1, 1) = V(0, 1);
		A(1, 2) = V(1, 1);
		A(1, 3) = V(2, 1);
		A(2, 0) = -V(0, 2) - V(1, 2) - V(2, 2);
		A(2, 1) = V(0, 2);
		A(2, 2) = V(1, 2);
		A(2, 3) = V(2, 2);
	}

	inline void fillCooSys_by_Mat(std::vector<Eigen::Triplet<real>>& cooSys, int row,
		int nTotalVerts, int* id, const Eigen::Matrix<real, 3, 4>& T)
	{
		// The matrix T is in block diag style:
		// | A 0 0 |
		// | 0 A 0 |
		// | 0 0 A |
		// where each A is a 3x4 matrix
		const static int nBlocks = 3;
		const static int nPoints = 4;
		const static int nCoords = 3;
		int pos = row * 4;
		for (int iBlock = 0; iBlock < nBlocks; iBlock++)
		{
			const int yb = iBlock * nCoords;
			for (int y = 0; y < nCoords; y++)
			{
				for (int x = 0; x < nPoints; x++)
				{
					const int col = nTotalVerts * iBlock + id[x];
					cooSys[pos++] = Eigen::Triplet<real>(row + yb + y, col, T(y, x));
				}
			}
		} // end for iBlock
	}

	void MeshTransfer::setup_E1Mat(const std::vector<Float3>& tarVerts0)
	{
		const int nMeshVerts = (int)tarVerts0.size();
		const int nTotalVerts = nMeshVerts + (int)m_facesTri.size();
		std::vector<Eigen::Triplet<real>> cooSys;

		m_E1Rhs.resize(m_facesTri.size() * 9);
		cooSys.resize(m_E1Rhs.size() * 4);

		Eigen::Matrix<real, 3, 4> Ti;
		Ti.setZero();
		Int4 id_vi_tar;
		Float3 vi_tar[4];
		for (int iFace = 0; iFace < (int)m_facesTri.size(); iFace++)
		{
			// face_i_tar
			fill4VertsOfFace(iFace, m_facesTri, tarVerts0, id_vi_tar.data(), vi_tar);
			getMatrix_namedby_T(vi_tar, Ti);

			// construct the gradient transfer matrix
			bool inValid = hasIllegalData(Ti.data(), (int)Ti.size());
			if (inValid)
				Ti.setZero();

			// push matrix
			const int row = iFace * 9;
			fillCooSys_by_Mat(cooSys, row, nTotalVerts, id_vi_tar.data(), Ti);
		}

		m_E1Mat.resize((int)m_E1Rhs.size(), nTotalVerts * 3);
		if (cooSys.size() > 0)
			m_E1Mat.setFromTriplets(cooSys.begin(), cooSys.end());
	}

	void MeshTransfer::setup_E1Rhs(const std::vector<Float3>& srcVertsDeformed)
	{
		const int nMeshVerts = (int)srcVertsDeformed.size();
		m_E1Rhs.resize(m_facesTri.size() * 9);
		Eigen::Matrix<real, 3, 4> Si_A;
		Eigen::Matrix<real, 4, 1> Si_x[3];
		Eigen::Matrix<real, 3, 1> Si_b[3];
		Si_A.setZero();
		Int4 id_vi_src0, id_vi_src1;
		Float3 vi_src0[4], vi_src1[4];
		for (int iFace = 0; iFace < (int)m_facesTri.size(); iFace++)
		{
			// face_i_src
			fill4VertsOfFace(iFace, m_facesTri, m_srcVerts0, id_vi_src0.data(), vi_src0);
			fill4VertsOfFace(iFace, m_facesTri, srcVertsDeformed, id_vi_src1.data(), vi_src1);

			// construct the gradient transfer matrix
			getMatrix_namedby_T(vi_src0, Si_A);
			bool inValid = hasIllegalData(Si_A.data(), (int)Si_A.size());
			for (int k = 0; k < 4; k++)
			{
				Si_x[0][k] = vi_src1[k][0];
				Si_x[1][k] = vi_src1[k][1];
				Si_x[2][k] = vi_src1[k][2];
			}
			if (inValid)
			{
				Si_A.setZero();
				Si_x[0].setZero();
				Si_x[1].setZero();
				Si_x[2].setZero();
			}
			Si_b[0] = Si_A * Si_x[0];
			Si_b[1] = Si_A * Si_x[1];
			Si_b[2] = Si_A * Si_x[2];

			// push matrix
			const int row = iFace * 9;
			m_E1Rhs[row + 0] = Si_b[0][0];
			m_E1Rhs[row + 1] = Si_b[0][1];
			m_E1Rhs[row + 2] = Si_b[0][2];

			m_E1Rhs[row + 3] = Si_b[1][0];
			m_E1Rhs[row + 4] = Si_b[1][1];
			m_E1Rhs[row + 5] = Si_b[1][2];

			m_E1Rhs[row + 6] = Si_b[2][0];
			m_E1Rhs[row + 7] = Si_b[2][1];
			m_E1Rhs[row + 8] = Si_b[2][2];
		}
	}

	void MeshTransfer::setup_ancorMat()
	{
		const int nMeshVerts = (int)m_srcVerts0.size();
		const int nTotalVerts = nMeshVerts + (int)m_facesTri.size();
		m_ancorMat.resize((int)m_anchors.size() * 3, nTotalVerts * 3);

		// build matrix
		for (int i = 0; i < m_anchors.size(); i++)
		{
			for (int k = 0; k < 3; k++)
				m_ancorMat.insert(i * 3 + k, m_anchors[i] + nTotalVerts*k) = 1;
		}
		m_ancorMat.finalize();
	}

	void MeshTransfer::setup_ancorRhs(const std::vector<Float3>& tarVerts0)
	{
		const int nMeshVerts = (int)tarVerts0.size();
		const int nTotalVerts = nMeshVerts + (int)m_facesTri.size();
		m_ancorRhs.resize((int)m_anchors.size() * 3);
		m_ancorRhs.setZero();

		// build matrix
		for (int i = 0; i < m_anchors.size(); i++)
		{
			for (int k = 0; k < 3; k++)
				m_ancorRhs[i * 3 + k] = tarVerts0[m_anchors[i]][k];
		}
	}

	void MeshTransfer::setup_pairMat()
	{
		if (m_vertPairs.empty())
			return;
		const int nMeshVerts = (int)m_srcVerts0.size();
		const int nTotalVerts = nMeshVerts + (int)m_facesTri.size();

		std::vector<Eigen::Triplet<real>> cooSys;
		std::vector<float> cooRhs;

		int row = 0;
		for (const auto& pair : m_vertPairs)
		{
			for (int k = 0; k < 3; k++)
			{
				cooSys.push_back(Eigen::Triplet<real>(row + k, pair[0] + k * nTotalVerts, 1));
				cooSys.push_back(Eigen::Triplet<real>(row + k, pair[1] + k * nTotalVerts, -1));
			}
			row += 3;
		} // end for pair

		m_pairMat.resize(row, nTotalVerts * 3);
		if (cooSys.size())
			m_pairMat.setFromTriplets(cooSys.begin(), cooSys.end());
		m_pairMatT = m_pairMat.transpose();

		printf("pairMat of %d pairs setup\n", (int)m_vertPairs.size());
	}

	void MeshTransfer::setup_pairRhs(const std::vector<Float3>& tarVerts0)
	{
		if (m_vertPairs.empty())
			return;
		const int nMeshVerts = (int)m_srcVerts0.size();
		const int nTotalVerts = nMeshVerts + (int)m_facesTri.size();

		std::vector<float> cooRhs;
		for (const auto& pair : m_vertPairs)
		{
			const Float3 d = tarVerts0[pair[0]] - tarVerts0[pair[1]];
			for (int k = 0; k < 3; k++)
				cooRhs.push_back(d[k]);
		} // end for pair

		m_pairRhs.resize(cooRhs.size());
		for (int r = 0; r < cooRhs.size(); r++)
			m_pairRhs[r] = cooRhs[r];
	}

	void MeshTransfer::setup_RegularizationMat()
	{
		const int nMeshVerts = (int)m_srcVerts0.size();
		const int nTotalVerts = nMeshVerts + (int)m_facesTri.size();
		m_regAtA.resize(nTotalVerts * 3, nTotalVerts * 3);
		m_regAtA.reserve(nTotalVerts * 3);
		for (int row = 0; row < m_regAtA.rows(); row++)
			m_regAtA.insert(row, row) = 1;
		m_regAtA.finalize();
	}

	void MeshTransfer::setup_RegularizationRhs(const std::vector<Float3>& tarVerts0)
	{
		const int nMeshVerts = (int)m_srcVerts0.size();
		const int nTotalVerts = nMeshVerts + (int)m_facesTri.size();
		m_regAtb.resize(nTotalVerts * 3);
		m_regAtb.setZero();
		for (int iVert = 0; iVert < nMeshVerts; iVert++)
		{
			for (int k = 0; k < 3; k++)
				m_regAtb[iVert + k * nTotalVerts] = tarVerts0[iVert][k];
		}
	}
