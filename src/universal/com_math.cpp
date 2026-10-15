// universal/com_math.cpp
//
// Reconstructed from the PS4 dedicated server (iw6_ds_ps4, PDB iw6mp64_dh_server_orbis, changelist 715098).
// Functions appear in original line order; each is tagged with its address in that build and its original line.

#include <math.h>
#include <stdlib.h>
#include <pmmintrin.h>

#include <iw6_static.h>

#include "universal/com_math.h"

#define IW6_SOURCE "universal/com_math.cpp"

// Defined elsewhere in the original: universal/com_vector.h inlines emitted out of line in other objects,
// universal/com_math_anglevectors.cpp, universal/com_vector4_const.cpp, and QuatTransform (an inline the linker
// kept from DynEntity_Hinge.obj).
extern const float vec3_origin[3];
extern const __m128 g_negativeZero;
float Vec3Normalize(float *const v);
float Vec4Normalize(float *const v);
void AngleVectors(const float *const angles, float *const forward, float *const right, float *const up);
void QuatTransform(const float *quat, const float *in, float *out);

// Quantized unit directions, defined in this file (162 entries; data, linked from the original).
extern float bytedirs[162][3];

// Random number state for I_flrand / I_irand (file static).
IW6_STATIC unsigned int holdrand IW6_AT("", "holdrand");

// Header inlines used below (no out-of-line copy in the original binary).
static inline float I_fsel(const float comparand, const float valGE, const float valLT)
{
	return comparand >= 0.0f ? valGE : valLT;
}

static inline float AngleNormalize180(const float angle)
{
	const float scaled = angle * (1.0f / 360.0f);
	return (scaled - floorf(scaled + 0.5f)) * 360.0f;
}

// 14022E060  universal/com_math.cpp:200
float I_random()
{
	return rand() * (1.0f / 32768.0f);
}

// 14022FA60  universal/com_math.cpp:235
int RandWithSeed(int *seed)
{
	*seed = (int)(1103515245u * (unsigned int)*seed + 12345u);
	return (*seed / 65536) & 0x7FFF;
}

// 14022E230  universal/com_math.cpp:418
float LinearTrack(float tgt, float cur, float rate, float deltaTime)
{
	float step = rate * deltaTime;
	const float err = tgt - cur;
	if (!(err > 0.0f))
		step = -step;

	const float errAbs = (float)fabs(err);
	if (errAbs > 0.001f && !((float)fabs(step) > errAbs))
		return step + cur;
	return tgt;
}

// 14022E2B0  universal/com_math.cpp:446
float LinearTrackAngle(float tgt, float cur, float rate, float deltaTime)
{
	while (tgt - cur > 180.0f)
		tgt -= 360.0f;
	while (tgt - cur < -180.0f)
		tgt += 360.0f;

	float step = rate * deltaTime;
	const float err = tgt - cur;
	if (!(err > 0.0f))
		step = -step;

	const float errAbs = (float)fabs(err);
	if (errAbs > 0.001f && !((float)fabs(step) > errAbs))
		tgt = step + cur;
	return AngleNormalize180(tgt);
}

// 14022DC10  universal/com_math.cpp:466
float DiffTrack(float tgt, float cur, float rate, float deltaTime)
{
	const float err = tgt - cur;
	const float step = err * rate * deltaTime;

	const float errAbs = (float)fabs(err);
	if (errAbs > 0.001f && !((float)fabs(step) > errAbs))
		return step + cur;
	return tgt;
}

// 14022DC80  universal/com_math.cpp:490
float DiffTrackAngle(float tgt, float cur, float rate, float deltaTime)
{
	while (tgt - cur > 180.0f)
		tgt -= 360.0f;
	while (tgt - cur < -180.0f)
		tgt += 360.0f;

	const float err = tgt - cur;
	const float step = err * rate * deltaTime;

	const float errAbs = (float)fabs(err);
	if (errAbs > 0.001f && !((float)fabs(step) > errAbs))
		tgt = step + cur;
	return AngleNormalize180(tgt);
}

// 14022DF70  universal/com_math.cpp:505
float GraphGetValueFromFraction(const int knotCount, const float (*knots)[2], const float fraction)
{
	for (int knotIndex = 1; knotIndex < knotCount; ++knotIndex)
	{
		if (knots[knotIndex][0] - knots[knotIndex - 1][0] == 0.0f)
			continue;
		if (knots[knotIndex][0] >= fraction)
		{
			const float adjustedFrac = (fraction - knots[knotIndex - 1][0])
			                         / (knots[knotIndex][0] - knots[knotIndex - 1][0]);
			return adjustedFrac * (knots[knotIndex][1] - knots[knotIndex - 1][1]) + knots[knotIndex - 1][1];
		}
	}
	return -1.0f;
}

// 14022F4E0  universal/com_math.cpp:574
float Q_acos(const float c)
{
	const float angle = acosf(c);
	if (angle > 3.14159265f)
		return 3.14159265f;
	if (angle < -3.14159265f)
		return -3.14159265f;
	return angle;
}

// 14022DD90  universal/com_math.cpp:634
unsigned char DirToByte(const float *const dir)
{
	if (!dir)
		return 0;

	unsigned char best = 0;
	float bestd = 0.0f;
	for (unsigned char i = 0; i < 162; ++i)
	{
		const float d = dir[0] * bytedirs[i][0] + dir[1] * bytedirs[i][1] + dir[2] * bytedirs[i][2];
		if (d > bestd)
		{
			bestd = d;
			best = i;
		}
	}
	return best;
}

// 1402304C0  universal/com_math.cpp:675
int VecNCompareCustomEpsilon(const float *const v0, const float *const v1, float epsilon, int coordCount)
{
	const float epsilonSq = epsilon * epsilon;
	for (int i = 0; i < coordCount; ++i)
	{
		const float delta = v0[i] - v1[i];
		if (delta * delta > epsilonSq)
			return 0;
	}
	return 1;
}

// 1402301F0  universal/com_math.cpp:719
float Vec2Distance(const float *const v1, const float *const v2)
{
	const float dx = v2[0] - v1[0];
	const float dy = v2[1] - v1[1];
	return sqrtf(dy * dy + dx * dx);
}

// 140230220  universal/com_math.cpp:733
float Vec2DistanceSq(const float *const p1, const float *const p2)
{
	const float dx = p2[0] - p1[0];
	const float dy = p2[1] - p1[1];
	return dy * dy + dx * dx;
}

// 140230240  universal/com_math.cpp:828
float Vec2Normalize(float *const v)
{
	const float length = sqrtf(v[0] * v[0] + v[1] * v[1]);
	const float lengthInv = 1.0f / I_fsel(-length, 1.0f, length);
	v[0] *= lengthInv;
	v[1] *= lengthInv;
	return length;
}

// 1402302C0  universal/com_math.cpp:845
float Vec2NormalizeTo(const float *const v, float *const out)
{
	const float length = sqrtf(v[0] * v[0] + v[1] * v[1]);
	const float lengthInv = 1.0f / I_fsel(-length, 1.0f, length);
	out[0] = v[0] * lengthInv;
	out[1] = v[1] * lengthInv;
	return length;
}

// 140230340  universal/com_math.cpp:862
void Vec2Rotate(const float *const in, float angle, float *const out)
{
	const float s = sinf(angle);
	const float c = cosf(angle);
	out[0] = c * in[0] - s * in[1];
	out[1] = s * in[0] + c * in[1];
}

// 140230440  universal/com_math.cpp:888
void Vec3RotateTranspose(const float *const in, const float (*const matrix)[3], float *const out)
{
	out[0] = in[0] * matrix[0][0] + in[1] * matrix[1][0] + in[2] * matrix[2][0];
	out[1] = in[0] * matrix[0][1] + in[1] * matrix[1][1] + in[2] * matrix[2][1];
	out[2] = in[0] * matrix[0][2] + in[1] * matrix[1][2] + in[2] * matrix[2][2];
}

// 14022FB40  universal/com_math.cpp:897
void RotationMatrix(const float *__restrict dir, float radians, float (*__restrict matrix)[3])
{
	const float c = cosf(radians);
	const float omc = 1.0f - c;
	const float s = sinf(radians);

	const float xOmc = dir[0] * omc;
	const float yOmc = dir[1] * omc;
	const float zOmc = dir[2] * omc;
	const float xs = dir[0] * s;
	const float ys = dir[1] * s;
	const float zs = dir[2] * s;

	matrix[0][0] = dir[0] * xOmc + c;
	matrix[0][1] = dir[0] * yOmc - zs;
	matrix[0][2] = dir[2] * xOmc + ys;
	matrix[1][0] = dir[0] * yOmc + zs;
	matrix[1][1] = dir[1] * yOmc + c;
	matrix[1][2] = dir[1] * zOmc - xs;
	matrix[2][0] = dir[2] * xOmc - ys;
	matrix[2][1] = dir[1] * zOmc + xs;
	matrix[2][2] = dir[2] * zOmc + c;
}

// 14022FA80  universal/com_math.cpp:931
void RotatePointAroundVector(float *const dst, const float *const dir, const float *const point, float degrees)
{
	float matrix[3][3];
	RotationMatrix(dir, degrees * (3.14159265f / 180.0f), matrix);
	dst[0] = matrix[0][0] * point[0] + matrix[0][1] * point[1] + matrix[0][2] * point[2];
	dst[1] = matrix[1][0] * point[0] + matrix[1][1] * point[1] + matrix[1][2] * point[2];
	dst[2] = matrix[2][0] * point[0] + matrix[2][1] * point[1] + matrix[2][2] * point[2];
}

// 1402303B0  universal/com_math.cpp:949
void Vec3Basis_RightHanded(const float *const forward, float *const left, float *const up)
{
	PerpendicularVector(forward, up);
	left[0] = up[1] * forward[2] - up[2] * forward[1];
	left[1] = up[2] * forward[0] - up[0] * forward[2];
	left[2] = up[0] * forward[1] - up[1] * forward[0];
}

// 140230A90  universal/com_math.cpp:961
float vectoyaw(const float *const vec)
{
	if (vec[1] == 0.0f && vec[0] == 0.0f)
		return 0.0f;

	const float yaw = atan2f(vec[1], vec[0]) * (180.0f / 3.14159265f);
	return yaw + I_fsel(yaw, 0.0f, 360.0f);
}

// 140230A50  universal/com_math.cpp:984
float vectosignedyaw(const float *const vec)
{
	if (vec[1] == 0.0f && vec[0] == 0.0f)
		return 0.0f;

	return atan2f(vec[1], vec[0]) * (180.0f / 3.14159265f);
}

// 1402308C0  universal/com_math.cpp:1009
float vectopitch(const float *const vec)
{
	if (vec[1] == 0.0f && vec[0] == 0.0f)
		return I_fsel(-vec[2], 90.0f, 270.0f);

	const float forward = sqrtf(vec[0] * vec[0] + vec[1] * vec[1]);
	const float pitch = atan2f(vec[2], forward) * (-180.0f / 3.14159265f);
	return pitch + I_fsel(pitch, 0.0f, 360.0f);
}

// 1402307B0  universal/com_math.cpp:1058
void vectoangles(const float *const vec, float *const angles)
{
	float yaw;
	float pitch;

	if (vec[1] == 0.0f && vec[0] == 0.0f)
	{
		yaw = 0.0f;
		pitch = I_fsel(-vec[2], 90.0f, 270.0f);
	}
	else
	{
		yaw = atan2f(vec[1], vec[0]) * (180.0f / 3.14159265f);
		yaw += I_fsel(yaw, 0.0f, 360.0f);

		const float forward = sqrtf(vec[0] * vec[0] + vec[1] * vec[1]);
		pitch = atan2f(vec[2], forward) * (-180.0f / 3.14159265f);
		pitch += I_fsel(pitch, 0.0f, 360.0f);
	}

	angles[0] = pitch;
	angles[1] = yaw;
	angles[2] = 0.0f;
}

// 140230010  universal/com_math.cpp:1084
void UnitQuatToAngles(const float *const quat, float *const angles)
{
	float axis[3][3];
	UnitQuatToAxis(quat, axis);
	AxisToAngles(axis, angles);
}

// 140230970  universal/com_math.cpp:1098
void vectosignedangles(const float *const vec, float *const angles)
{
	float yaw;
	float pitch;

	if (vec[1] == 0.0f && vec[0] == 0.0f)
	{
		yaw = 0.0f;
		pitch = I_fsel(-vec[2], 90.0f, -90.0f);
	}
	else
	{
		yaw = atan2f(vec[1], vec[0]) * (180.0f / 3.14159265f);
		const float forward = sqrtf(vec[0] * vec[0] + vec[1] * vec[1]);
		pitch = atan2f(vec[2], forward) * (-180.0f / 3.14159265f);
	}

	angles[0] = pitch;
	angles[1] = yaw;
	angles[2] = 0.0f;
}

// 140230730  universal/com_math.cpp:1126
void YawVectors(const float yaw, float *const forward, float *const right)
{
	const float angle = yaw * (3.14159265f / 180.0f);
	const float sy = sinf(angle);
	const float cy = cosf(angle);
	if (forward)
	{
		forward[0] = cy;
		forward[1] = sy;
		forward[2] = 0.0f;
	}
	if (right)
	{
		right[0] = sy;
		right[1] = -cy;
		right[2] = 0.0f;
	}
}

// 1402306C0  universal/com_math.cpp:1152
void YawVectors2D(const float yaw, float *const forward, float *const right)
{
	const float angle = yaw * (3.14159265f / 180.0f);
	const float sy = sinf(angle);
	const float cy = cosf(angle);
	if (forward)
	{
		forward[0] = cy;
		forward[1] = sy;
	}
	if (right)
	{
		right[0] = sy;
		right[1] = -cy;
	}
}

// 14022F210  universal/com_math.cpp:1181
void PerpendicularVector(const float *const src, float *const dst)
{
	float srcSq[3];
	srcSq[0] = src[0] * src[0];
	srcSq[1] = src[1] * src[1];
	srcSq[2] = src[2] * src[2];

	int pos = srcSq[0] > srcSq[1];
	if (srcSq[pos] > srcSq[2])
		pos = 2;

	const float scale = -src[pos];
	dst[0] = src[0] * scale;
	dst[1] = src[1] * scale;
	dst[2] = src[2] * scale;
	dst[pos] += 1.0f;
	Vec3Normalize(dst);
}

// 14022F3D0  universal/com_math.cpp:1373
float PointToLineSegmentDistSq2D(const float *const point, const float *const start, const float *const end)
{
	const float pointDelta[2] = { point[0] - start[0], point[1] - start[1] };
	const float segment[2] = { end[0] - start[0], end[1] - start[1] };

	const float dot = pointDelta[1] * segment[1] + pointDelta[0] * segment[0];
	if (dot < 0.0f)
		return pointDelta[1] * pointDelta[1] + pointDelta[0] * pointDelta[0];

	const float segmentLenSq = segment[1] * segment[1] + segment[0] * segment[0];
	if (dot > segmentLenSq)
	{
		const float endDelta[2] = { point[0] - end[0], point[1] - end[1] };
		return endDelta[1] * endDelta[1] + endDelta[0] * endDelta[0];
	}

	const float scale = -(dot / segmentLenSq);
	const float perp[2] = { scale * segment[0] + pointDelta[0], scale * segment[1] + pointDelta[1] };
	return perp[1] * perp[1] + perp[0] * perp[0];
}

// 14022F350  universal/com_math.cpp:1444
float PointOnLineClosestToPoint(const float *const pt, const float *const start, const float *const dir,
                                float *const result)
{
	const float t = (pt[1] - start[1]) * dir[1] + dir[0] * (pt[0] - start[0]) + (pt[2] - start[2]) * dir[2];
	result[0] = dir[0] * t + start[0];
	result[1] = t * dir[1] + start[1];
	result[2] = t * dir[2] + start[2];
	return t;
}

// 14022CF60  universal/com_math.cpp:1462
void ClosestApproachOfTwoLines(const float *const p1, const float *const dir1, const float *const p2,
                               const float *const dir2, float *s, float *t)
{
	const float dir1LenSq = dir1[0] * dir1[0] + dir1[1] * dir1[1] + dir1[2] * dir1[2];
	const float dir2LenSq = dir2[0] * dir2[0] + dir2[1] * dir2[1] + dir2[2] * dir2[2];
	const float negDirDot = -(dir2[0] * dir1[0] + dir2[1] * dir1[1] + dir2[2] * dir1[2]);
	const float delta[3] = { p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2] };
	const float dir1DotDelta = dir1[0] * delta[0] + dir1[1] * delta[1] + dir1[2] * delta[2];
	const float det = dir2LenSq * dir1LenSq - negDirDot * negDirDot;

	// fabs here is VC11's C++ fabs(float) overload, (float)fabs((double)x)
	if (det * det > (float)__builtin_fabs(negDirDot * dir1LenSq) * 0.0001f)
	{
		const float invDet = 1.0f / det;
		const float negDir2DotDelta = -(dir2[0] * delta[0] + dir2[1] * delta[1] + dir2[2] * delta[2]);
		*s = (negDir2DotDelta * negDirDot - dir1DotDelta * dir2LenSq) * invDet;
		*t = (dir1DotDelta * negDirDot - negDir2DotDelta * dir1LenSq) * invDet;
	}
	else
	{
		// the lines are (nearly) parallel
		*s = -(dir1DotDelta / dir1LenSq);
		*t = 0.0f;
	}
}

// 14022E3B0  universal/com_math.cpp:1523
void MatrixIdentity44(float (*const out)[4])
{
	out[0][0] = 1.0f;
	out[0][1] = 0.0f;
	out[0][2] = 0.0f;
	out[0][3] = 0.0f;
	out[1][0] = 0.0f;
	out[1][1] = 1.0f;
	out[1][2] = 0.0f;
	out[1][3] = 0.0f;
	out[2][0] = 0.0f;
	out[2][1] = 0.0f;
	out[2][2] = 1.0f;
	out[2][3] = 0.0f;
	out[3][0] = 0.0f;
	out[3][1] = 0.0f;
	out[3][2] = 0.0f;
	out[3][3] = 1.0f;
}

// 14022EE10  universal/com_math.cpp:1532
void MatrixSet44(float (*const out)[4], const float *const origin, const float (*const axis)[3], float scale)
{
	out[0][0] = scale * axis[0][0];
	out[0][1] = scale * axis[0][1];
	out[0][2] = scale * axis[0][2];
	out[0][3] = 0.0f;
	out[1][0] = scale * axis[1][0];
	out[1][1] = scale * axis[1][1];
	out[1][2] = scale * axis[1][2];
	out[1][3] = 0.0f;
	out[2][0] = scale * axis[2][0];
	out[2][1] = scale * axis[2][1];
	out[2][2] = scale * axis[2][2];
	out[2][3] = 0.0f;
	out[3][0] = origin[0];
	out[3][1] = origin[1];
	out[3][2] = origin[2];
	out[3][3] = 1.0f;
}

// 14022EC80  universal/com_math.cpp:1561
void MatrixMultiply(const float (*const in1)[3], const float (*const in2)[3], float (*const out)[3])
{
	out[0][0] = in1[0][0] * in2[0][0] + in1[0][1] * in2[1][0] + in1[0][2] * in2[2][0];
	out[0][1] = in1[0][1] * in2[1][1] + in1[0][0] * in2[0][1] + in1[0][2] * in2[2][1];
	out[0][2] = in1[0][1] * in2[1][2] + in1[0][0] * in2[0][2] + in1[0][2] * in2[2][2];
	out[1][0] = in1[1][1] * in2[1][0] + in1[1][0] * in2[0][0] + in1[1][2] * in2[2][0];
	out[1][1] = in1[1][1] * in2[1][1] + in1[1][0] * in2[0][1] + in1[1][2] * in2[2][1];
	out[1][2] = in1[1][1] * in2[1][2] + in1[1][0] * in2[0][2] + in1[1][2] * in2[2][2];
	out[2][0] = in1[2][1] * in2[1][0] + in1[2][0] * in2[0][0] + in1[2][2] * in2[2][0];
	out[2][1] = in1[2][1] * in2[1][1] + in1[2][0] * in2[0][1] + in1[2][2] * in2[2][1];
	out[2][2] = in1[2][1] * in2[1][2] + in1[2][0] * in2[0][2] + in1[2][2] * in2[2][2];
}

// 14022E910  universal/com_math.cpp:1644
void MatrixMultiply43(const float (*const in1)[3], const float (*const in2)[3], float (*const out)[3])
{
	out[0][0] = in1[0][0] * in2[0][0] + in1[0][1] * in2[1][0] + in1[0][2] * in2[2][0];
	out[1][0] = in1[1][1] * in2[1][0] + in1[1][0] * in2[0][0] + in1[1][2] * in2[2][0];
	out[2][0] = in1[2][1] * in2[1][0] + in1[2][0] * in2[0][0] + in1[2][2] * in2[2][0];
	out[0][1] = in1[0][1] * in2[1][1] + in1[0][0] * in2[0][1] + in1[0][2] * in2[2][1];
	out[1][1] = in1[1][1] * in2[1][1] + in1[1][0] * in2[0][1] + in1[1][2] * in2[2][1];
	out[2][1] = in1[2][1] * in2[1][1] + in1[2][0] * in2[0][1] + in1[2][2] * in2[2][1];
	out[0][2] = in1[0][0] * in2[0][2] + in1[0][1] * in2[1][2] + in1[0][2] * in2[2][2];
	out[1][2] = in1[1][1] * in2[1][2] + in1[1][0] * in2[0][2] + in1[1][2] * in2[2][2];
	out[2][2] = in1[2][1] * in2[1][2] + in1[2][0] * in2[0][2] + in1[2][2] * in2[2][2];
	out[3][0] = in1[3][1] * in2[1][0] + in1[3][0] * in2[0][0] + in1[3][2] * in2[2][0] + in2[3][0];
	out[3][1] = in1[3][1] * in2[1][1] + in1[3][0] * in2[0][1] + in1[3][2] * in2[2][1] + in2[3][1];
	out[3][2] = in1[3][1] * in2[1][2] + in1[3][0] * in2[0][2] + in1[3][2] * in2[2][2] + in2[3][2];
}

// 14022EB30  universal/com_math.cpp:1668
void MatrixMultiply44(const float (*const in1)[4], const float (*const in2)[4], float (*const out)[4])
{
	// both inputs are read in full before out is written, so out may alias either of them
	float result[4][4];
	for (int i = 0; i < 3; ++i)
	{
		for (int j = 0; j < 4; ++j)
			result[i][j] = in1[i][1] * in2[1][j] + in1[i][0] * in2[0][j] + in1[i][2] * in2[2][j]
			             + in1[i][3] * in2[3][j];
	}
	for (int j = 0; j < 4; ++j)
		result[3][j] = in1[3][0] * in2[0][j] + in1[3][1] * in2[1][j] + in1[3][2] * in2[2][j] + in1[3][3] * in2[3][j];

	for (int i = 0; i < 4; ++i)
	{
		for (int j = 0; j < 4; ++j)
			out[i][j] = result[i][j];
	}
}

// 14022EF90  universal/com_math.cpp:1739
void MatrixTranspose44(const float *const in, float *const out)
{
	float result[16];
	for (int i = 0; i < 4; ++i)
	{
		for (int j = 0; j < 4; ++j)
			result[4 * i + j] = in[4 * j + i];
	}
	for (int i = 0; i < 16; ++i)
		out[i] = result[i];
}

// 14022E680  universal/com_math.cpp:1780
void MatrixInverse(const float (*const in)[3], float (*const out)[3])
{
	const float cofactor00 = in[1][1] * in[2][2] - in[1][2] * in[2][1];
	const float det = cofactor00 * in[0][0] - (in[0][1] * in[2][2] - in[0][2] * in[2][1]) * in[1][0]
	                + (in[0][1] * in[1][2] - in[0][2] * in[1][1]) * in[2][0];
	const float invDet = 1.0f / det;

	out[0][0] = cofactor00 * invDet;
	out[0][1] = -((in[0][1] * in[2][2] - in[2][1] * in[0][2]) * invDet);
	out[0][2] = (in[0][1] * in[1][2] - in[0][2] * in[1][1]) * invDet;
	out[1][0] = -((in[1][0] * in[2][2] - in[2][0] * in[1][2]) * invDet);
	out[1][1] = (in[0][0] * in[2][2] - in[0][2] * in[2][0]) * invDet;
	out[1][2] = -((in[0][0] * in[1][2] - in[0][2] * in[1][0]) * invDet);
	out[2][0] = (in[2][1] * in[1][0] - in[2][0] * in[1][1]) * invDet;
	out[2][1] = -((in[2][1] * in[0][0] - in[0][1] * in[2][0]) * invDet);
	out[2][2] = (in[1][1] * in[0][0] - in[0][1] * in[1][0]) * invDet;
}

// 14022E830  universal/com_math.cpp:1811
void MatrixInverseOrthogonal43(const float (*const in)[3], float (*const out)[3])
{
	out[0][0] = in[0][0];
	out[0][1] = in[1][0];
	out[0][2] = in[2][0];
	out[1][0] = in[0][1];
	out[1][1] = in[1][1];
	out[1][2] = in[2][1];
	out[2][0] = in[0][2];
	out[2][1] = in[1][2];
	out[2][2] = in[2][2];

	const float negOrigin[3] = {
		vec3_origin[0] - in[3][0],
		vec3_origin[1] - in[3][1],
		vec3_origin[2] - in[3][2],
	};
	out[3][0] = negOrigin[1] * out[1][0] + negOrigin[0] * out[0][0] + negOrigin[2] * out[2][0];
	out[3][1] = negOrigin[1] * out[1][1] + negOrigin[0] * out[0][1] + negOrigin[2] * out[2][1];
	out[3][2] = negOrigin[0] * out[0][2] + negOrigin[1] * out[1][2] + negOrigin[2] * out[2][2];
}

// 14022E3E0  universal/com_math.cpp:1822
//
// Intel's SSE inverse by Cramer's rule ("Streaming SIMD Extensions - Inverse of 4x4 Matrix"), with the
// determinant summed by haddps and its reciprocal from rcpss refined by one Newton-Raphson step. mat and dst
// are 16-byte aligned.
__attribute__((target("sse3"))) void MatrixInverse44(const float *const mat, float *const dst)
{
	__m128 minor0, minor1, minor2, minor3;
	__m128 row0, row1, row2, row3;
	__m128 det, tmp1;

	// transposed rows; row1 and row3 have their halves swapped
	const __m128 src0 = _mm_load_ps(mat);
	const __m128 src1 = _mm_load_ps(mat + 4);
	const __m128 src2 = _mm_load_ps(mat + 8);
	const __m128 src3 = _mm_load_ps(mat + 12);
	tmp1 = _mm_shuffle_ps(src0, src1, 0x44);
	row1 = _mm_shuffle_ps(src2, src3, 0x44);
	row0 = _mm_shuffle_ps(tmp1, row1, 0x88);
	row1 = _mm_shuffle_ps(row1, tmp1, 0xDD);
	tmp1 = _mm_shuffle_ps(src0, src1, 0xEE);
	row3 = _mm_shuffle_ps(src2, src3, 0xEE);
	row2 = _mm_shuffle_ps(tmp1, row3, 0x88);
	row3 = _mm_shuffle_ps(row3, tmp1, 0xDD);

	tmp1 = _mm_mul_ps(row3, row2);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0xB1);
	minor0 = _mm_mul_ps(row1, tmp1);
	minor1 = _mm_mul_ps(row0, tmp1);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0x4E);
	minor0 = _mm_sub_ps(_mm_mul_ps(row1, tmp1), minor0);
	minor1 = _mm_sub_ps(_mm_mul_ps(row0, tmp1), minor1);
	minor1 = _mm_shuffle_ps(minor1, minor1, 0x4E);

	tmp1 = _mm_mul_ps(row2, row1);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0xB1);
	minor0 = _mm_add_ps(minor0, _mm_mul_ps(row3, tmp1));
	minor3 = _mm_mul_ps(row0, tmp1);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0x4E);
	minor0 = _mm_sub_ps(minor0, _mm_mul_ps(row3, tmp1));
	minor3 = _mm_sub_ps(_mm_mul_ps(row0, tmp1), minor3);
	minor3 = _mm_shuffle_ps(minor3, minor3, 0x4E);

	tmp1 = _mm_mul_ps(_mm_shuffle_ps(row1, row1, 0x4E), row3);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0xB1);
	row2 = _mm_shuffle_ps(row2, row2, 0x4E);
	minor0 = _mm_add_ps(minor0, _mm_mul_ps(row2, tmp1));
	minor2 = _mm_mul_ps(row0, tmp1);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0x4E);
	minor0 = _mm_sub_ps(minor0, _mm_mul_ps(row2, tmp1));
	minor2 = _mm_sub_ps(_mm_mul_ps(row0, tmp1), minor2);
	minor2 = _mm_shuffle_ps(minor2, minor2, 0x4E);

	tmp1 = _mm_mul_ps(row1, row0);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0xB1);
	minor2 = _mm_add_ps(minor2, _mm_mul_ps(row3, tmp1));
	minor3 = _mm_sub_ps(_mm_mul_ps(row2, tmp1), minor3);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0x4E);
	minor2 = _mm_sub_ps(_mm_mul_ps(row3, tmp1), minor2);
	minor3 = _mm_sub_ps(minor3, _mm_mul_ps(row2, tmp1));

	tmp1 = _mm_mul_ps(row3, row0);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0xB1);
	minor1 = _mm_sub_ps(minor1, _mm_mul_ps(row2, tmp1));
	minor2 = _mm_add_ps(minor2, _mm_mul_ps(row1, tmp1));
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0x4E);
	minor1 = _mm_add_ps(minor1, _mm_mul_ps(row2, tmp1));
	minor2 = _mm_sub_ps(minor2, _mm_mul_ps(row1, tmp1));

	tmp1 = _mm_mul_ps(row2, row0);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0xB1);
	minor1 = _mm_add_ps(minor1, _mm_mul_ps(row3, tmp1));
	minor3 = _mm_sub_ps(minor3, _mm_mul_ps(row1, tmp1));
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0x4E);
	minor1 = _mm_sub_ps(minor1, _mm_mul_ps(row3, tmp1));
	minor3 = _mm_add_ps(minor3, _mm_mul_ps(row1, tmp1));

	det = _mm_mul_ps(minor0, row0);
	det = _mm_hadd_ps(det, det);
	det = _mm_hadd_ps(det, det);
	tmp1 = _mm_rcp_ss(det);
	det = _mm_sub_ss(_mm_add_ss(tmp1, tmp1), _mm_mul_ss(det, _mm_mul_ss(tmp1, tmp1)));
	det = _mm_shuffle_ps(det, det, 0x00);

	_mm_store_ps(dst, _mm_mul_ps(det, minor0));
	_mm_store_ps(dst + 4, _mm_mul_ps(minor1, det));
	_mm_store_ps(dst + 8, _mm_mul_ps(minor2, det));
	_mm_store_ps(dst + 12, _mm_mul_ps(minor3, det));
}

// 14022EF40  universal/com_math.cpp:1930
void MatrixTransformVector44(const float *const vec, const float (*const mat)[4], float *const out)
{
	// Multiply-add with g_negativeZero as the addend (-0 leaves every sum unchanged). vec, mat and out are
	// 16-byte aligned.
	const __m128 v = _mm_load_ps(vec);
	__m128 sumYW = _mm_add_ps(_mm_mul_ps(_mm_shuffle_ps(v, v, 0x55), _mm_load_ps(mat[1])), g_negativeZero);
	__m128 sumXZ = _mm_add_ps(_mm_mul_ps(_mm_shuffle_ps(v, v, 0x00), _mm_load_ps(mat[0])), g_negativeZero);
	sumYW = _mm_add_ps(sumYW, _mm_mul_ps(_mm_shuffle_ps(v, v, 0xFF), _mm_load_ps(mat[3])));
	sumXZ = _mm_add_ps(sumXZ, _mm_mul_ps(_mm_shuffle_ps(v, v, 0xAA), _mm_load_ps(mat[2])));
	_mm_store_ps(out, _mm_add_ps(sumYW, sumXZ));
}

// 14022F0C0  universal/com_math.cpp:1967
void MatrixTransposeTransformVector(const float *const in1, const float (*const in2)[3], float *const out)
{
	out[0] = in2[0][1] * in1[1] + in2[0][0] * in1[0] + in2[0][2] * in1[2];
	out[1] = in2[1][0] * in1[0] + in2[1][1] * in1[1] + in2[1][2] * in1[2];
	out[2] = in2[2][0] * in1[0] + in2[2][1] * in1[1] + in2[2][2] * in1[2];
}

// 14022F0C0  universal/com_math.cpp:1967
// Folded by the linker with MatrixTransposeTransformVector (identical code).
void Vec3Rotate(const float *const in, const float (*const matrix)[3], float *const out)
{
	out[0] = matrix[0][1] * in[1] + matrix[0][0] * in[0] + matrix[0][2] * in[2];
	out[1] = matrix[1][0] * in[0] + matrix[1][1] * in[1] + matrix[1][2] * in[2];
	out[2] = matrix[2][0] * in[0] + matrix[2][1] * in[1] + matrix[2][2] * in[2];
}

// 14022EEB0  universal/com_math.cpp:1981
void MatrixTransformVector43(const float *const in1, const float (*const in2)[3], float *const out)
{
	out[0] = in2[1][0] * in1[1] + in2[0][0] * in1[0] + in2[2][0] * in1[2] + in2[3][0];
	out[1] = in2[0][1] * in1[0] + in2[1][1] * in1[1] + in2[2][1] * in1[2] + in2[3][1];
	out[2] = in2[0][2] * in1[0] + in2[1][2] * in1[1] + in2[2][2] * in1[2] + in2[3][2];
}

// 14022F020  universal/com_math.cpp:1995
void MatrixTransposeTransformVector43(const float *const in1, const float (*const in2)[3], float *const out)
{
	const float temp[3] = { in1[0] - in2[3][0], in1[1] - in2[3][1], in1[2] - in2[3][2] };
	out[0] = temp[1] * in2[0][1] + temp[0] * in2[0][0] + temp[2] * in2[0][2];
	out[1] = temp[1] * in2[1][1] + temp[0] * in2[1][0] + temp[2] * in2[1][2];
	out[2] = temp[1] * in2[2][1] + temp[0] * in2[2][0] + temp[2] * in2[2][2];
}

// 140230500  universal/com_math.cpp:2030
void VectorAngleMultiply(float *const vec, float angle)
{
	const float radians = angle * 0.017453292f;
	const float s = sinf(radians);
	const float c = cosf(radians);
	const float x = vec[0];
	const float y = vec[1];
	vec[0] = x * c - y * s;
	vec[1] = y * c + x * s;
}

// 14022F520  universal/com_math.cpp:2049
void QuatInverse(const float *in, float *out)
{
	out[0] = -in[0];
	out[1] = -in[1];
	out[2] = -in[2];
	out[3] = in[3];
}

// 14022F8E0  universal/com_math.cpp:2063
void QuatToAxis(const float *const quat, float (*const axis)[3])
{
	float xx = quat[0] * quat[0];
	float yy = quat[1] * quat[1];
	float zz = quat[2] * quat[2];
	const float ww = quat[3] * quat[3];
	const float scale = 2.0f / (xx + yy + zz + ww);

	const float xs = quat[0] * scale;
	const float ys = quat[1] * scale;
	const float zs = quat[2] * scale;
	xx *= scale;
	yy *= scale;
	zz *= scale;

	const float xy = quat[1] * xs;
	const float xz = quat[2] * xs;
	const float yz = quat[2] * ys;
	const float wx = quat[3] * xs;
	const float wy = quat[3] * ys;
	const float wz = zs * quat[3];

	axis[0][0] = 1.0f - (zz + yy);
	axis[0][1] = wz + xy;
	axis[0][2] = xz - wy;
	axis[1][0] = xy - wz;
	axis[1][1] = 1.0f - (zz + xx);
	axis[1][2] = yz + wx;
	axis[2][0] = wy + xz;
	axis[2][1] = yz - wx;
	axis[2][2] = 1.0f - (yy + xx);
}

// 140230040  universal/com_math.cpp:2108
void UnitQuatToAxis(const float *const quat, float (*const axis)[3])
{
	const float x2 = quat[0] + quat[0];
	const float xx = quat[0] * x2;
	const float xy = quat[1] * x2;
	const float xz = quat[2] * x2;
	const float wx = quat[3] * x2;

	const float y2 = quat[1] + quat[1];
	const float yy = quat[1] * y2;
	const float yz = quat[2] * y2;
	const float wy = quat[3] * y2;

	const float z2 = quat[2] + quat[2];
	const float zz = quat[2] * z2;
	const float wz = quat[3] * z2;

	axis[0][0] = 1.0f - (zz + yy);
	axis[0][1] = wz + xy;
	axis[0][2] = xz - wy;
	axis[1][0] = xy - wz;
	axis[1][1] = 1.0f - (zz + xx);
	axis[1][2] = yz + wx;
	axis[2][0] = wy + xz;
	axis[2][1] = yz - wx;
	axis[2][2] = 1.0f - (yy + xx);
}

// 140230170  universal/com_math.cpp:2144
void UnitQuatToForward(const float *const quat, float *const forward)
{
	forward[0] = 1.0f - (quat[1] * quat[1] + quat[2] * quat[2]) * 2.0f;
	forward[1] = (quat[0] * quat[1] + quat[3] * quat[2]) * 2.0f;
	forward[2] = (quat[0] * quat[2] - quat[3] * quat[1]) * 2.0f;
}

// 14022F6B0  universal/com_math.cpp:2154
void QuatNlerp(const float *const from, const float *const to, float frac, float *const result)
{
	const float dot = to[0] * from[0] + to[1] * from[1] + to[2] * from[2] + to[3] * from[3];
	const float toScale = (dot >= 0.0f ? 1.0f : -1.0f) * frac;
	const float fromScale = 1.0f - frac;

	result[0] = toScale * to[0] + from[0] * fromScale;
	result[1] = toScale * to[1] + fromScale * from[1];
	result[2] = toScale * to[2] + fromScale * from[2];
	result[3] = toScale * to[3] + fromScale * from[3];
	Vec4Normalize(result);
}

// 14022F770  universal/com_math.cpp:2168
void QuatSlerp(const float *const from, const float *const to, float frac, float *const result)
{
	float fromScale;
	float toScale;

	const float dot = to[0] * from[0] + to[1] * from[1] + to[2] * from[2] + to[3] * from[3];
	const float sign = dot >= 0.0f ? 1.0f : -1.0f;
	const float cosom = sign * dot;
	if (cosom > 0.95f)
	{
		// nearly parallel: a plain lerp is accurate enough, and the result is normalized below anyway
		fromScale = 1.0f - frac;
		toScale = frac;
	}
	else
	{
		const float omega = acosf(cosom);
		fromScale = sinf(omega - omega * frac);
		toScale = sinf(omega * frac);
	}
	toScale *= sign;

	result[0] = toScale * to[0] + from[0] * fromScale;
	result[1] = toScale * to[1] + fromScale * from[1];
	result[2] = toScale * to[2] + fromScale * from[2];
	result[3] = toScale * to[3] + fromScale * from[3];
	Vec4Normalize(result);
}

// 14022FCC0  universal/com_math.cpp:2275
float RotationToYaw(const float *const rot)
{
	// rot is a rotation about z only: (z, w) of the quaternion
	const float zz = rot[0] * rot[0];
	const float scale = 2.0f / (rot[1] * rot[1] + zz);
	return atan2f(rot[1] * rot[0] * scale, 1.0f - scale * zz) * 57.295776f;
}

// 14022C640  universal/com_math.cpp:2364
void AngleAxisToQuat(float angle, const float *const axis, float *const quat)
{
	const float halfAngle = angle * 0.5f;
	quat[3] = cosf(halfAngle);
	const float s = sinf(halfAngle);
	quat[0] = s * axis[0];
	quat[1] = s * axis[1];
	quat[2] = s * axis[2];
}

// 14022C750  universal/com_math.cpp:2593
void AnglesSubtract(const float *const v1, const float *const v2, float *const v3)
{
	v3[0] = AngleDelta(v1[0], v2[0]);
	v3[1] = AngleDelta(v1[1], v2[1]);
	v3[2] = AngleDelta(v1[2], v2[2]);
}

// 14022C700  universal/com_math.cpp:2608
float AngleNormalize360(const float angle)
{
	const float scaled = angle * (1.0f / 360.0f);
	const float result = (scaled - floorf(scaled)) * 360.0f;
	if (result - 360.0f >= 0.0f)
		return result - 360.0f;
	return result;
}

// 14022C6B0  universal/com_math.cpp:2628
float AngleDelta(const float angle1, const float angle2)
{
	const float scaled = (angle1 - angle2) * (1.0f / 360.0f);
	return (scaled - floorf(scaled + 0.5f)) * 360.0f;
}

// 14022CAB0  universal/com_math.cpp:2711
void AxisClear(float (*const axis)[3])
{
	axis[0][0] = 1.0f;
	axis[0][1] = 0.0f;
	axis[0][2] = 0.0f;
	axis[1][0] = 0.0f;
	axis[1][1] = 1.0f;
	axis[1][2] = 0.0f;
	axis[2][0] = 0.0f;
	axis[2][1] = 0.0f;
	axis[2][2] = 1.0f;
}

// 14022CAE0  universal/com_math.cpp:2730
void AxisCopy(const float (*const in)[3], float (*const out)[3])
{
	out[0][0] = in[0][0];
	out[0][1] = in[0][1];
	out[0][2] = in[0][2];
	out[1][0] = in[1][0];
	out[1][1] = in[1][1];
	out[1][2] = in[1][2];
	out[2][0] = in[2][0];
	out[2][1] = in[2][1];
	out[2][2] = in[2][2];
}

// 14022EFE0  universal/com_math.cpp:2738
void AxisTranspose(const float (*const in)[3], float (*const out)[3])
{
	out[0][0] = in[0][0];
	out[0][1] = in[1][0];
	out[0][2] = in[2][0];
	out[1][0] = in[0][1];
	out[1][1] = in[1][1];
	out[1][2] = in[2][1];
	out[2][0] = in[0][2];
	out[2][1] = in[1][2];
	out[2][2] = in[2][2];
}

// 14022EFE0  universal/com_math.cpp:2738
// The linker folded this with AxisTranspose (identical code), so both names share one address and line.
void MatrixTranspose(const float (*const in)[3], float (*const out)[3])
{
	out[0][0] = in[0][0];
	out[0][1] = in[1][0];
	out[0][2] = in[2][0];
	out[1][0] = in[0][1];
	out[1][1] = in[1][1];
	out[1][2] = in[2][1];
	out[2][0] = in[0][2];
	out[2][1] = in[1][2];
	out[2][2] = in[2][2];
}

// 140230620  universal/com_math.cpp:2799
void YawToAxis(float yaw, float (*const axis)[3])
{
	float right[3];

	YawVectors(yaw, axis[0], right);
	axis[2][0] = 0.0f;
	axis[2][1] = 0.0f;
	axis[2][2] = 1.0f;
	axis[1][0] = vec3_origin[0] - right[0];
	axis[1][1] = vec3_origin[1] - right[1];
	axis[1][2] = vec3_origin[2] - right[2];
}

// 14022CB20  universal/com_math.cpp:2819
void AxisToAngles(const float (*const axis)[3], float *const angles)
{
	float temp[3];
	float right[3];
	float roll;

	// first get the pitch and yaw from the forward vector
	vectoangles(axis[0], angles);

	// rotate the right vector by the negative yaw, then by the negative pitch
	const float yaw = -angles[1] * 0.0174532925f;
	const float sy = sinf(yaw);
	const float cy = cosf(yaw);
	temp[0] = axis[1][0] * cy - axis[1][1] * sy;
	temp[1] = axis[1][1] * cy + axis[1][0] * sy;
	temp[2] = axis[1][2];

	const float pitch = -angles[0] * 0.0174532925f;
	const float sp = sinf(pitch);
	const float cp = cosf(pitch);
	right[0] = temp[2] * sp + temp[0] * cp;
	right[1] = temp[1];
	right[2] = temp[2] * cp - temp[0] * sp;

	// the roll is the pitch of what is left
	if (right[1] == 0.0f && right[0] == 0.0f)
		roll = -right[2] >= 0.0f ? 90.0f : -90.0f;
	else
		roll = atan2f(right[2], sqrtf(right[1] * right[1] + right[0] * right[0])) * -57.295776f;

	if (right[1] < 0.0f)
	{
		if (roll < 0.0f)
			angles[2] = roll + 180.0f;
		else
			angles[2] = roll + -180.0f;
	}
	else
	{
		angles[2] = -roll;
	}
}

// 14022E080  universal/com_math.cpp:3313
int IsPosInsideArc(const float *const pos, float posRadius, const float *const arcOrigin, float arcRadius,
                   float arcAngle0, float arcAngle1, float arcHalfHeight)
{
	float delta[2];

	delta[0] = pos[0] - arcOrigin[0];
	delta[1] = pos[1] - arcOrigin[1];
	const float dist = Vec2Normalize(delta);

	const float radiusDelta = dist - posRadius;
	if (radiusDelta * radiusDelta > arcRadius * arcRadius)
		return 0;
	if (arcOrigin[2] - arcHalfHeight > pos[2])
		return 0;
	if (pos[2] > arcOrigin[2] + arcHalfHeight)
		return 0;

	const float yaw = AngleNormalize360(vectoyaw(delta));
	if (arcAngle0 < arcAngle1)
	{
		if (arcAngle1 > yaw && yaw > arcAngle0)
			return 1;
	}
	else
	{
		if (arcAngle1 > yaw || yaw > arcAngle0)
			return 1;
	}
	return 0;
}

// 14022D410  universal/com_math.cpp:3374
float ColorNormalize(const float *const in, float *const out)
{
	float max = in[0];
	if (in[1] > max)
		max = in[1];
	if (in[2] > max)
		max = in[2];

	if (max == 0.0f)
	{
		out[2] = 1.0f;
		out[1] = 1.0f;
		out[0] = 1.0f;
		return 0.0f;
	}

	const float scale = 1.0f / max;
	out[0] = in[0] * scale;
	out[1] = scale * in[1];
	out[2] = scale * in[2];
	return max;
}

// 140230580  universal/com_math.cpp:3463
void VectorRotateQuatAroundPoint(const float *const vIn, const float *const vQuat, const float *const vOrigin,
                                 float *const out)
{
	float vDelta[3];
	float vRotatedDelta[3];

	vDelta[0] = vIn[0] - vOrigin[0];
	vDelta[1] = vIn[1] - vOrigin[1];
	vDelta[2] = vIn[2] - vOrigin[2];
	QuatTransform(vQuat, vDelta, vRotatedDelta);
	out[0] = vOrigin[0] + vRotatedDelta[0];
	out[1] = vRotatedDelta[1] + vOrigin[1];
	out[2] = vRotatedDelta[2] + vOrigin[2];
}

// 14022F2C0  universal/com_math.cpp:3501
float PitchForYawOnNormal(const float fYaw, const float *const normal)
{
	const float yaw = fYaw * 0.0174532925f;
	const float c = cosf(yaw);
	const float s = sinf(yaw);
	if (normal[2] == 0.0f)
		return 270.0f;
	return atanf((s * normal[1] + c * normal[0]) / normal[2]) * 180.0f / 3.14159265f;
}

// 14022F140  universal/com_math.cpp:3531
void NearestPitchAndYawOnPlane(const float *const angles, const float *const normal, float *const result)
{
	float forward[3];
	float projected[3];

	AngleVectors(angles, forward, nullptr, nullptr);
	const float d = -(normal[0] * forward[0] + normal[1] * forward[1] + normal[2] * forward[2]);
	projected[0] = normal[0] * d + forward[0];
	projected[1] = normal[1] * d + forward[1];
	projected[2] = normal[2] * d + forward[2];
	vectoangles(projected, result);
}

// 14022DFF0  universal/com_math.cpp:3563
float I_flrand(float min, float max)
{
	holdrand = holdrand * 214013 + 2531011;
	return (float)(holdrand >> 17) * (max - min) * (1.0f / 32768.0f) + min;
}

// 14022E030  universal/com_math.cpp:3577
int I_irand(int min, int max)
{
	holdrand = holdrand * 214013 + 2531011;
	return min + (int)(((__int64)(holdrand >> 17) * (max - min)) >> 15);
}

// 14022CCD0  universal/com_math.cpp:3657
void AxisToQuat(const float (*const mat)[3], float *const out)
{
	float test[4][4];
	float testSizeSq;
	int best;
	float invLength;

	test[0][0] = mat[1][2] - mat[2][1];
	test[0][1] = mat[2][0] - mat[0][2];
	test[0][2] = mat[0][1] - mat[1][0];
	test[0][3] = mat[0][0] + mat[1][1] + mat[2][2] + 1.0f;
	testSizeSq = test[0][0] * test[0][0] + test[0][1] * test[0][1] + test[0][2] * test[0][2] + test[0][3] * test[0][3];
	if (testSizeSq >= 1.0f)
	{
		best = 0;
	}
	else
	{
		test[1][0] = mat[0][2] + mat[2][0];
		test[1][1] = mat[2][1] + mat[1][2];
		test[1][2] = mat[2][2] - mat[1][1] - mat[0][0] + 1.0f;
		test[1][3] = test[0][2];
		testSizeSq = test[1][0] * test[1][0] + test[1][1] * test[1][1] + test[1][2] * test[1][2] + test[1][3] * test[1][3];
		if (testSizeSq >= 1.0f)
		{
			best = 1;
		}
		else
		{
			test[2][0] = mat[0][0] - mat[1][1] - mat[2][2] + 1.0f;
			test[2][1] = mat[1][0] + mat[0][1];
			test[2][2] = test[1][0];
			test[2][3] = test[0][0];
			testSizeSq = test[2][0] * test[2][0] + test[2][1] * test[2][1] + test[2][2] * test[2][2] + test[2][3] * test[2][3];
			if (testSizeSq >= 1.0f)
			{
				best = 2;
			}
			else
			{
				test[3][0] = test[2][1];
				test[3][1] = mat[1][1] - mat[0][0] - mat[2][2] + 1.0f;
				test[3][2] = test[1][1];
				test[3][3] = test[0][1];
				testSizeSq = test[3][0] * test[3][0] + test[3][1] * test[3][1] + test[3][2] * test[3][2] + test[3][3] * test[3][3];
				best = 3;
			}
		}
	}
	invLength = 1.0f / sqrtf(testSizeSq);
	out[0] = invLength * test[best][0];
	out[1] = invLength * test[best][1];
	out[2] = invLength * test[best][2];
	out[3] = invLength * test[best][3];
}

// 14022C820  universal/com_math.cpp:3663
void Axis4ToQuat(const float (*const mat)[4], float *const out)
{
	float test[4][4];
	float testSizeSq;
	int best;
	float invLength;

	test[0][0] = mat[1][2] - mat[2][1];
	test[0][1] = mat[2][0] - mat[0][2];
	test[0][2] = mat[0][1] - mat[1][0];
	test[0][3] = mat[0][0] + mat[1][1] + mat[2][2] + 1.0f;
	testSizeSq = test[0][0] * test[0][0] + test[0][1] * test[0][1] + test[0][2] * test[0][2] + test[0][3] * test[0][3];
	if (testSizeSq >= 1.0f)
	{
		best = 0;
	}
	else
	{
		test[1][0] = mat[0][2] + mat[2][0];
		test[1][1] = mat[2][1] + mat[1][2];
		test[1][2] = mat[2][2] - mat[1][1] - mat[0][0] + 1.0f;
		test[1][3] = test[0][2];
		testSizeSq = test[1][0] * test[1][0] + test[1][1] * test[1][1] + test[1][2] * test[1][2] + test[1][3] * test[1][3];
		if (testSizeSq >= 1.0f)
		{
			best = 1;
		}
		else
		{
			test[2][0] = mat[0][0] - mat[1][1] - mat[2][2] + 1.0f;
			test[2][1] = mat[1][0] + mat[0][1];
			test[2][2] = test[1][0];
			test[2][3] = test[0][0];
			testSizeSq = test[2][0] * test[2][0] + test[2][1] * test[2][1] + test[2][2] * test[2][2] + test[2][3] * test[2][3];
			if (testSizeSq >= 1.0f)
			{
				best = 2;
			}
			else
			{
				test[3][0] = test[2][1];
				test[3][1] = mat[1][1] - mat[0][0] - mat[2][2] + 1.0f;
				test[3][2] = test[1][1];
				test[3][3] = test[0][1];
				testSizeSq = test[3][0] * test[3][0] + test[3][1] * test[3][1] + test[3][2] * test[3][2] + test[3][3] * test[3][3];
				best = 3;
			}
		}
	}
	invLength = 1.0f / sqrtf(testSizeSq);
	out[0] = invLength * test[best][0];
	out[1] = invLength * test[best][1];
	out[2] = invLength * test[best][2];
	out[3] = invLength * test[best][3];
}

// 14022F560  universal/com_math.cpp:3669
void QuatLerp(const float *const qa, const float *const qb, float frac, float *const out)
{
	const float dot = qa[0] * qb[0] + qa[1] * qb[1] + qa[2] * qb[2] + qa[3] * qb[3];
	if (dot >= 0.0f)
	{
		out[0] = (qb[0] - qa[0]) * frac + qa[0];
		out[1] = (qb[1] - qa[1]) * frac + qa[1];
		out[2] = (qb[2] - qa[2]) * frac + qa[2];
		out[3] = (qb[3] - qa[3]) * frac + qa[3];
	}
	else
	{
		out[0] = -qb[0];
		out[1] = -qb[1];
		out[2] = -qb[2];
		out[3] = -qb[3];
		out[0] = (out[0] - qa[0]) * frac + qa[0];
		out[1] = (out[1] - qa[1]) * frac + qa[1];
		out[2] = (out[2] - qa[2]) * frac + qa[2];
		out[3] = (out[3] - qa[3]) * frac + qa[3];
	}
}

// 14022D480  universal/com_math.cpp:3772
bool CullBoxFromCone(const float *const coneOrg, const float *const coneDir, float cosHalfFov, const Bounds *bounds)
{
	float delta[3];
	float corner[3];
	float perp[3];
	float dir[3];

	delta[0] = bounds->midPoint[0] - coneOrg[0];
	delta[1] = bounds->midPoint[1] - coneOrg[1];
	delta[2] = bounds->midPoint[2] - coneOrg[2];
	corner[0] = bounds->halfSize[0] * (coneDir[0] >= 0.0f ? 1.0f : -1.0f);
	corner[1] = bounds->halfSize[1] * (coneDir[1] >= 0.0f ? 1.0f : -1.0f);
	corner[2] = bounds->halfSize[2] * (coneDir[2] >= 0.0f ? 1.0f : -1.0f);

	const float dist = coneDir[0] * delta[0] + coneDir[1] * delta[1] + coneDir[2] * delta[2];
	if (dist >= coneDir[0] * corner[0] + coneDir[1] * corner[1] + coneDir[2] * corner[2])
		return true;

	perp[0] = -dist * coneDir[0] + delta[0];
	perp[1] = -dist * coneDir[1] + delta[1];
	perp[2] = -dist * coneDir[2] + delta[2];
	const float perpLenSq = perp[0] * perp[0] + perp[1] * perp[1] + perp[2] * perp[2];
	const float cosSq = cosHalfFov * cosHalfFov;
	const float sinSq = 1.0f - cosSq;
	if (dist * dist * sinSq >= cosSq * perpLenSq)
		return false;

	const float scale = cosHalfFov / sqrtf(sinSq * perpLenSq);
	dir[0] = perp[0] * scale + coneDir[0];
	dir[1] = perp[1] * scale + coneDir[1];
	dir[2] = perp[2] * scale + coneDir[2];
	return dir[0] * delta[0] + dir[1] * delta[1] + dir[2] * delta[2] - fabs(bounds->halfSize[0] * dir[0])
	           - fabs(bounds->halfSize[1] * dir[1]) - fabs(bounds->halfSize[2] * dir[2])
	       >= 0.0f;
}

// 14022DA40  universal/com_math.cpp:3831
bool CullBoxFromSphere(const float *const sphereOrg, float radius, const Bounds *bounds)
{
	float dist[3];

	dist[0] = fabs(sphereOrg[0] - bounds->midPoint[0]) - bounds->halfSize[0];
	if (!(dist[0] >= 0.0f))
		dist[0] = 0.0f;
	dist[1] = fabs(sphereOrg[1] - bounds->midPoint[1]) - bounds->halfSize[1];
	if (!(dist[1] >= 0.0f))
		dist[1] = 0.0f;
	dist[2] = fabs(sphereOrg[2] - bounds->midPoint[2]) - bounds->halfSize[2];
	if (!(dist[2] >= 0.0f))
		dist[2] = 0.0f;
	return dist[0] * dist[0] + dist[1] * dist[1] + dist[2] * dist[2] > radius * radius;
}

// 14022D720  universal/com_math.cpp:3866
bool CullBoxFromConicSectionOfSphere(const float *const coneOrg, const float *const coneDir, float cosHalfFov,
                                     float radius, const Bounds *bounds)
{
	float delta[3];
	float dist[3];
	float corner[3];
	float perp[3];
	float dir[3];

	delta[0] = bounds->midPoint[0] - coneOrg[0];
	delta[1] = bounds->midPoint[1] - coneOrg[1];
	delta[2] = bounds->midPoint[2] - coneOrg[2];

	// outside the sphere
	dist[0] = fabs(delta[0]) - bounds->halfSize[0];
	if (!(dist[0] >= 0.0f))
		dist[0] = 0.0f;
	dist[1] = fabs(delta[1]) - bounds->halfSize[1];
	if (!(dist[1] >= 0.0f))
		dist[1] = 0.0f;
	dist[2] = fabs(delta[2]) - bounds->halfSize[2];
	if (!(dist[2] >= 0.0f))
		dist[2] = 0.0f;
	if (dist[0] * dist[0] + dist[1] * dist[1] + dist[2] * dist[2] > radius * radius)
		return true;

	// outside the cone
	corner[0] = bounds->halfSize[0] * (coneDir[0] >= 0.0f ? 1.0f : -1.0f);
	corner[1] = bounds->halfSize[1] * (coneDir[1] >= 0.0f ? 1.0f : -1.0f);
	corner[2] = bounds->halfSize[2] * (coneDir[2] >= 0.0f ? 1.0f : -1.0f);

	const float coneDist = coneDir[0] * delta[0] + coneDir[1] * delta[1] + coneDir[2] * delta[2];
	if (coneDist >= coneDir[0] * corner[0] + coneDir[1] * corner[1] + coneDir[2] * corner[2])
		return true;

	perp[0] = -coneDist * coneDir[0] + delta[0];
	perp[1] = -coneDist * coneDir[1] + delta[1];
	perp[2] = -coneDist * coneDir[2] + delta[2];
	const float perpLenSq = perp[0] * perp[0] + perp[1] * perp[1] + perp[2] * perp[2];
	const float cosSq = cosHalfFov * cosHalfFov;
	const float sinSq = 1.0f - cosSq;
	if (coneDist * coneDist * sinSq >= cosSq * perpLenSq)
		return false;

	const float scale = cosHalfFov / sqrtf(sinSq * perpLenSq);
	dir[0] = perp[0] * scale + coneDir[0];
	dir[1] = perp[1] * scale + coneDir[1];
	dir[2] = perp[2] * scale + coneDir[2];
	return dir[0] * delta[0] + dir[1] * delta[1] + dir[2] * delta[2] - fabs(bounds->halfSize[0] * dir[0])
	           - fabs(bounds->halfSize[1] * dir[1]) - fabs(bounds->halfSize[2] * dir[2])
	       >= 0.0f;
}

// 14022DAF0  universal/com_math.cpp:3935
bool CullSphereFromCone(const float *const coneOrg, const float *const coneDir, float cosHalfFov,
                        const float *const sphereCenter, float radius)
{
	float delta[3];
	float perp[3];

	delta[0] = sphereCenter[0] - coneOrg[0];
	delta[1] = sphereCenter[1] - coneOrg[1];
	delta[2] = sphereCenter[2] - coneOrg[2];
	const float dist = coneDir[0] * delta[0] + coneDir[1] * delta[1] + coneDir[2] * delta[2];
	if (dist >= radius)
		return true;

	const float cosSq = cosHalfFov * cosHalfFov;
	perp[0] = -dist * coneDir[0] + delta[0];
	perp[1] = -dist * coneDir[1] + delta[1];
	perp[2] = -dist * coneDir[2] + delta[2];
	const float sinHalfFov = sqrtf(1.0f - cosSq);
	const float edgeDist = sinHalfFov * dist - radius;
	return (perp[0] * perp[0] + perp[1] * perp[1] + perp[2] * perp[2]) * cosSq >= edgeDist * edgeDist;
}

// 14022DE10  universal/com_math.cpp:3969
float DistanceFromConeToPoint(const float *const coneOrg, const float *const coneDir, float cosHalfFov,
                              const float *const point)
{
	float delta[3];
	float perp[3];

	delta[0] = point[0] - coneOrg[0];
	delta[1] = point[1] - coneOrg[1];
	delta[2] = point[2] - coneOrg[2];
	const float dist = coneDir[0] * delta[0] + coneDir[1] * delta[1] + coneDir[2] * delta[2];
	perp[0] = -dist * coneDir[0] + delta[0];
	perp[1] = -dist * coneDir[1] + delta[1];
	perp[2] = -dist * coneDir[2] + delta[2];
	const float perpDist = sqrtf(perp[0] * perp[0] + perp[1] * perp[1] + perp[2] * perp[2]);
	const float sinHalfFov = sqrtf(1.0f - cosHalfFov * cosHalfFov);

	if (dist * cosHalfFov > sinHalfFov * perpDist)
		return sqrtf(delta[0] * delta[0] + delta[1] * delta[1] + delta[2] * delta[2]);

	const float distToEdge = sinHalfFov * dist + perpDist * cosHalfFov;
	if (distToEdge <= 0.0f)
		return 0.0f;
	return distToEdge;
}

// 14022FDA0  universal/com_math.cpp:4139
void TrajectoryCalculateInitialVelocity(const float *const startPos, const float *const endPos,
                                        const float *const gravityVector, float totalTime, float *const returnVector)
{
	const float halfTimeSq = totalTime * 0.5f * totalTime;
	returnVector[0] = (endPos[0] - startPos[0] - halfTimeSq * gravityVector[0]) / totalTime;
	returnVector[1] = (endPos[1] - startPos[1] - halfTimeSq * gravityVector[1]) / totalTime;
	returnVector[2] = (endPos[2] - startPos[2] - halfTimeSq * gravityVector[2]) / totalTime;
}

// 14022FE10  universal/com_math.cpp:4157
float TrajectoryCalculateMinimumVelocity(const float *const startPos, const float *const endPos, float gravity)
{
	const float deltaX = endPos[0] - startPos[0];
	const float deltaY = endPos[1] - startPos[1];
	const float horizontalDistance = sqrtf(deltaX * deltaX + deltaY * deltaY);
	const float verticalDistance = endPos[2] - startPos[2];
	const float a = gravity * gravity * horizontalDistance * horizontalDistance;
	const float b = gravity * 2.0f * verticalDistance;
	return (float)sqrt((sqrt(a * 4.0 + b * b) + b) * 0.5);
}

// 14022FD20  universal/com_math.cpp:4192
float TrajectoryCalculateExitAngle(float velocity, float gravity, float horizontalDistance, float verticalDistance)
{
	const float velocitySq = velocity * velocity;
	const float root = sqrtf(velocitySq * velocity * velocity
	                         - (verticalDistance * 2.0f * velocity * velocity
	                            + gravity * horizontalDistance * horizontalDistance)
	                               * gravity);
	return atanf((velocitySq - root) / (gravity * horizontalDistance)) * (180.0f / 3.14159265358979323846f);
}

// 14022FEF0  universal/com_math.cpp:4215
float TrajectoryEstimateDesiredInAirTime(const float *const startPos, const float *const endPos, float velocity,
                                         float gravity)
{
	float delta[3];

	delta[0] = endPos[0] - startPos[0];
	delta[1] = endPos[1] - startPos[1];
	delta[2] = 0.0f;
	const float horizontalDistance = sqrtf(delta[0] * delta[0] + delta[1] * delta[1] + delta[2] * delta[2]);
	const float verticalDistance = endPos[2] - startPos[2];
	const float exitAngle = TrajectoryCalculateExitAngle(velocity, gravity, horizontalDistance, verticalDistance);
	return horizontalDistance / (cosf(exitAngle * (3.14159265358979323846f / 180.0f)) * velocity);
}

// 14022FED0  universal/com_math.cpp:4241
float TrajectoryComputeDeltaHeightAtTime(float verticalVelocity, float gravity, float time)
{
	return verticalVelocity * time + gravity * -0.5f * time * time;
}

// 14022D160  universal/com_math.cpp:4262
void ClosestPointsTwoSegs(float *const s00, float *const s01, float *const s10, float *const s11, float *t0, float *t1)
{
	float u[3];
	float v[3];
	float w[3];

	u[0] = s01[0] - s00[0];
	u[1] = s01[1] - s00[1];
	u[2] = s01[2] - s00[2];
	v[0] = s11[0] - s10[0];
	v[1] = s11[1] - s10[1];
	v[2] = s11[2] - s10[2];
	w[0] = s00[0] - s10[0];
	w[1] = s00[1] - s10[1];
	w[2] = s00[2] - s10[2];
	const float a = u[0] * u[0] + u[1] * u[1] + u[2] * u[2];
	const float b = u[0] * v[0] + u[1] * v[1] + u[2] * v[2];
	const float c = v[0] * v[0] + v[1] * v[1] + v[2] * v[2];
	const float d = u[0] * w[0] + u[1] * w[1] + u[2] * w[2];
	const float e = v[0] * w[0] + v[1] * w[1] + v[2] * w[2];
	const float D = a * c - b * b;
	float sN, sD = D;
	float tN, tD = D;

	if (D < 1e-06)
	{
		// the segments are almost parallel
		sN = 0.0f;
		sD = 1.0f;
		tN = e;
		tD = c;
	}
	else
	{
		sN = b * e - c * d;
		tN = a * e - b * d;
		if (sN < 0.0f)
		{
			sN = 0.0f;
			tN = e;
			tD = c;
		}
		else if (sN > sD)
		{
			sN = sD;
			tN = e + b;
			tD = c;
		}
	}

	if (tN < 0.0f)
	{
		tN = 0.0f;
		if (-d < 0.0f)
			sN = 0.0f;
		else if (-d > a)
			sN = sD;
		else
		{
			sN = -d;
			sD = a;
		}
	}
	else if (tN > tD)
	{
		tN = tD;
		if (b - d < 0.0f)
			sN = 0.0f;
		else if (b - d > a)
			sN = sD;
		else
		{
			sN = b - d;
			sD = a;
		}
	}

	*t0 = fabs(sN) < 0.0001f ? 0.0f : sN / sD;
	*t1 = fabs(tN) < 0.0001f ? 0.0f : tN / tD;
}
