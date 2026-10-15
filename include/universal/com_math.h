// universal/com_math.h: prototypes for universal/com_math.cpp.
//
// Exact signatures from the PS4 server's MAP decorated names (iw6_ds_ps4); the build checks every one, since a
// mismatch changes the decorated name. Matrix parameters are arrays of rows (float (*)[3] / [4]), as in the
// original. Declarations are in original line order.
#pragma once

struct Bounds
{
	float midPoint[3];
	float halfSize[3];
};

float I_random();
int RandWithSeed(int *seed);
float LinearTrack(float tgt, float cur, float rate, float deltaTime);
float LinearTrackAngle(float tgt, float cur, float rate, float deltaTime);
float DiffTrack(float tgt, float cur, float rate, float deltaTime);
float DiffTrackAngle(float tgt, float cur, float rate, float deltaTime);
float GraphGetValueFromFraction(const int knotCount, const float (*knots)[2], const float fraction);
float Q_acos(const float c);
unsigned char DirToByte(const float *const dir);
int VecNCompareCustomEpsilon(const float *const v0, const float *const v1, float epsilon, int coordCount);
float Vec2Distance(const float *const v1, const float *const v2);
float Vec2DistanceSq(const float *const p1, const float *const p2);
float Vec2Normalize(float *const v);
float Vec2NormalizeTo(const float *const v, float *const out);
void Vec2Rotate(const float *const in, float angle, float *const out);
void Vec3RotateTranspose(const float *const in, const float (*const matrix)[3], float *const out);
void RotationMatrix(const float *__restrict axis, float angle, float (*__restrict out)[3]);
void RotatePointAroundVector(float *const dst, const float *const dir, const float *const point, float degrees);
void Vec3Basis_RightHanded(const float *const forward, float *const left, float *const up);
float vectoyaw(const float *const vec);
float vectosignedyaw(const float *const vec);
float vectopitch(const float *const vec);
void vectoangles(const float *const vec, float *const angles);
void UnitQuatToAngles(const float *const quat, float *const angles);
void vectosignedangles(const float *const vec, float *const angles);
void YawVectors(const float yaw, float *const forward, float *const right);
void YawVectors2D(const float yaw, float *const forward, float *const right);
void PerpendicularVector(const float *const src, float *const dst);
float PointToLineSegmentDistSq2D(const float *const point, const float *const start, const float *const end);
float PointOnLineClosestToPoint(const float *const point, const float *const lineStart, const float *const lineEnd,
                                float *const closest);
void ClosestApproachOfTwoLines(const float *const p1, const float *const dir1, const float *const p2,
                               const float *const dir2, float *s, float *t);
void MatrixIdentity44(float (*const out)[4]);
void MatrixSet44(float (*const out)[4], const float *const origin, const float (*const axis)[3], float scale);
void MatrixMultiply(const float (*const in1)[3], const float (*const in2)[3], float (*const out)[3]);
void MatrixMultiply43(const float (*const in1)[3], const float (*const in2)[3], float (*const out)[3]);
void MatrixMultiply44(const float (*const in1)[4], const float (*const in2)[4], float (*const out)[4]);
void MatrixTranspose44(const float *const in, float *const out);
void MatrixInverse(const float (*const in)[3], float (*const out)[3]);
void MatrixInverseOrthogonal43(const float (*const in)[3], float (*const out)[3]);
void MatrixInverse44(const float *const mat, float *const dst);
void MatrixTransformVector44(const float *const vec, const float (*const mat)[4], float *const out);
void MatrixTransposeTransformVector(const float *const in1, const float (*const in2)[3], float *const out);
void Vec3Rotate(const float *const in, const float (*const matrix)[3], float *const out);  // folded with the above
void MatrixTransformVector43(const float *const in1, const float (*const in2)[3], float *const out);
void MatrixTransposeTransformVector43(const float *const in1, const float (*const in2)[3], float *const out);
void VectorAngleMultiply(float *const vec, float angle);
void QuatInverse(const float *in, float *out);
void QuatToAxis(const float *const quat, float (*const axis)[3]);
void UnitQuatToAxis(const float *const quat, float (*const axis)[3]);
void UnitQuatToForward(const float *const quat, float *const forward);
void QuatNlerp(const float *const qa, const float *const qb, float frac, float *const out);
void QuatSlerp(const float *const from, const float *const to, float frac, float *const result);
float RotationToYaw(const float *const rot);
void AngleAxisToQuat(float angle, const float *const axis, float *const quat);
void AnglesSubtract(const float *const v1, const float *const v2, float *const v3);
float AngleNormalize360(const float angle);
float AngleDelta(const float angle1, const float angle2);
void AxisClear(float (*const axis)[3]);
void AxisCopy(const float (*const in)[3], float (*const out)[3]);
void AxisTranspose(const float (*const in)[3], float (*const out)[3]);
void MatrixTranspose(const float (*const in)[3], float (*const out)[3]);  // folded with AxisTranspose
void YawToAxis(float yaw, float (*const axis)[3]);
void AxisToAngles(const float (*const axis)[3], float *const angles);
int IsPosInsideArc(const float *const pos, float posRadius, const float *const arcOrigin, float arcRadius,
                   float arcAngle0, float arcAngle1, float arcHalfHeight);
float ColorNormalize(const float *const in, float *const out);
void VectorRotateQuatAroundPoint(const float *const in, const float *const point, const float *const quat,
                                 float *const out);
float PitchForYawOnNormal(const float fYaw, const float *const normal);
void NearestPitchAndYawOnPlane(const float *const angles, const float *const normal, float *const result);
float I_flrand(float min, float max);
int I_irand(int min, int max);
void AxisToQuat(const float (*const mat)[3], float *const out);
void Axis4ToQuat(const float (*const mat)[4], float *const out);
void QuatLerp(const float *const qa, const float *const qb, float frac, float *const out);
bool CullBoxFromCone(const float *const coneOrg, const float *const coneDir, float cosHalfFov, const Bounds *box);
bool CullBoxFromSphere(const float *const sphereOrg, float radius, const Bounds *box);
bool CullBoxFromConicSectionOfSphere(const float *const coneOrg, const float *const coneDir, float cosHalfFov,
                                     float radius, const Bounds *box);
bool CullSphereFromCone(const float *const coneOrg, const float *const coneDir, float cosHalfFov,
                        const float *const sphereCenter, float radius);
float DistanceFromConeToPoint(const float *const coneOrg, const float *const coneDir, float cosHalfFov,
                              const float *const point);
void TrajectoryCalculateInitialVelocity(const float *const start, const float *const end, const float *const gravity,
                                        float duration, float *const velocity);
float TrajectoryCalculateMinimumVelocity(const float *const start, const float *const end, float gravity);
float TrajectoryCalculateExitAngle(float velocity, float gravity, float distance, float height);
float TrajectoryEstimateDesiredInAirTime(const float *const start, const float *const end, float gravity,
                                         float velocity);
float TrajectoryComputeDeltaHeightAtTime(float velocity, float gravity, float time);
void ClosestPointsTwoSegs(float *const p1, float *const q1, float *const p2, float *const q2, float *s, float *t);
