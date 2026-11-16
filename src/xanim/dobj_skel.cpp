// xanim/dobj_skel.cpp (Store build): a model's bones from local space (the animation's output) to model space.
//
// The servers' PDBs place these in xanim/dobj_skel.cpp (CalcSkelRootBonesNoParentOrDuplicate line 143,
// CalcSkelNonRootBones line 279). The code is the Store build's, tagged with Store addresses, with its floating-point
// operation order (results are bit-exact); tools/fastfile/skin.py is the same in Python, checked against the game on
// real models (tests/fastfile/skin_check.py). docs/assets/models.md, Skinning.

#include "xanim/xmodel.h"

struct DSkelPartBits
{
	int anim[8];
	int control[8];
	int worldCtrl[8];
	int skel[8];
};

struct DSkel
{
	DSkelPartBits partBits;  // +0x00
	int timeStamp;           // +0x80
	DObjAnimMat *mat;        // +0x88
};
static_assert(sizeof(DSkel) == 0x90, "DSkel");
static_assert(__builtin_offsetof(DSkel, mat) == 0x88, "DSkel");

// The index of the highest set bit counted from the top (bit 31 -> 0), or 32 for no bit: bone i of a 32-bone word is
// bit 31 - i.
static inline unsigned int HighBitIndex(unsigned int bits)
{
	return bits ? (unsigned int)__builtin_clz(bits) : 32u;
}

// 2 / |q|^2, the factor that turns the quaternion into a rotation matrix; a degenerate quaternion becomes identity.
// The test is in double precision, as in the Store build (CVTPS2PD, COMISD against 1e-6, JBE): a NaN length takes
// the identity branch too.
static inline void SetTransWeight(DObjAnimMat *mat)
{
	float lenSq = ((mat->quat[1] * mat->quat[1] + mat->quat[0] * mat->quat[0]) + mat->quat[2] * mat->quat[2])
	              + mat->quat[3] * mat->quat[3];
	if (!((double)lenSq > 1e-6))
	{
		mat->quat[3] = 1.0f;
		mat->transWeight = 2.0f;
	}
	else
		mat->transWeight = 2.0f / lenSq;
}

// Store 140556990
// The root bones (numRootBones from minBoneIndex) are already in model space: each still to calculate only gets its
// transWeight, and its bit in calcPartBits cleared.
void CalcSkelRootBonesNoParentOrDuplicate(const XModel *model, DSkel *skel, int minBoneIndex, int *const calcPartBits)
{
	DObjAnimMat *mats = skel->mat;
	int maxBoneIndex = model->numRootBones + minBoneIndex;
	int wordIndex = minBoneIndex >> 5;
	int remaining = maxBoneIndex - wordIndex * 32;
	for (; wordIndex <= (maxBoneIndex - 1) >> 5; ++wordIndex, remaining -= 32)
	{
		unsigned int bits = (unsigned int)calcPartBits[wordIndex];
		int limit = remaining < 0x21 ? remaining : 0x20;
		for (;;)
		{
			unsigned int bit = HighBitIndex(bits);
			if ((int)bit >= limit)
				break;
			bits &= ~(0x80000000u >> bit);
			calcPartBits[wordIndex] = (int)bits;
			SetTransWeight(&mats[wordIndex * 32 + (int)bit]);
		}
	}
}

// Store 1405561D0
// Every other bone still to calculate (bones minBoneIndex .. minBoneIndex + numBones - numRootBones - 1):
// rotation parent * local (a control bone: root * local * root^-1 * parent, its local rotation being relative to the
// root's frame; a world-control bone keeps its rotation as it is), then translation: the local offset, scaled by the
// model's scale unless the bone is in noScalePartBits, plus the base translation, rotated by the parent and added to
// the parent's translation. Parents come before their children, so one pass is enough.
void CalcSkelNonRootBones(const XModel *model, DSkel *skel, int minBoneIndex, int *const calcPartBits,
                          const int *const controlPartBits, const int *const worldControlPartBits)
{
	float scale = model->scale;
	DObjAnimMat *mats = skel->mat;
	int maxBoneIndex = (model->numBones - model->numRootBones) + minBoneIndex;
	int wordIndex = minBoneIndex >> 5;
	int remaining = maxBoneIndex - wordIndex * 32;
	for (; wordIndex <= (maxBoneIndex - 1) >> 5; ++wordIndex, remaining -= 32)
	{
		unsigned int bits = (unsigned int)calcPartBits[wordIndex];
		int limit = remaining < 0x21 ? remaining : 0x20;
		for (;;)
		{
			unsigned int bitIndex = HighBitIndex(bits);
			if ((int)bitIndex >= limit)
				break;
			unsigned int bit = 0x80000000u >> bitIndex;
			bits &= ~bit;
			int localIndex = wordIndex * 32 + (int)bitIndex - minBoneIndex;
			calcPartBits[wordIndex] = (int)bits;
			DObjAnimMat *mat = &mats[wordIndex * 32 + (int)bitIndex];
			const DObjAnimMat *parent = mat - model->parentList[localIndex];
			if (!((unsigned int)worldControlPartBits[wordIndex] & bit))
			{
				float x, y, z, w;
				if (!((unsigned int)controlPartBits[wordIndex] & bit))
				{
					float p0 = parent->quat[0], p1 = parent->quat[1], p2 = parent->quat[2], p3 = parent->quat[3];
					float c0 = mat->quat[0], c1 = mat->quat[1], c2 = mat->quat[2], c3 = mat->quat[3];
					x = ((p0 * c3 + c0 * p3) + c2 * p1) - c1 * p2;
					y = ((c1 * p3 - c2 * p0) + p1 * c3) + p2 * c0;
					w = ((c3 * p3 - p0 * c0) - c1 * p1) - p2 * c2;
					z = ((c1 * p0 + c2 * p3) - p1 * c0) + p2 * c3;
				}
				else
				{
					const DObjAnimMat *root = mats;
					float p0 = parent->quat[0], p1 = parent->quat[1], p2 = parent->quat[2], p3 = parent->quat[3];
					float r0 = root->quat[0], r1 = root->quat[1], r2 = root->quat[2], r3 = root->quat[3];
					// parent relative to the root: root^-1 * parent (unnormalised conjugate)
					float a0 = ((p0 * r3 - r0 * p3) - p2 * r1) + p1 * r2;
					float a1 = ((p2 * r0 + p1 * r3) - r1 * p3) - r2 * p0;
					float a2 = ((p2 * r3 - p1 * r0) + r1 * p0) - r2 * p3;
					float a3 = ((r0 * p0 + p3 * r3) + p1 * r1) + r2 * p2;
					float c0 = mat->quat[0], c1 = mat->quat[1], c2 = mat->quat[2], c3 = mat->quat[3];
					float b0 = ((c0 * a3 + a0 * c3) + c1 * a2) - c2 * a1;
					float b1 = ((c3 * a1 - c0 * a2) + c1 * a3) + a0 * c2;
					float b2 = ((c3 * a2 + c0 * a1) - a0 * c1) + c2 * a3;
					float b3 = ((c3 * a3 - a0 * c0) - c1 * a1) - c2 * a2;
					mat->quat[0] = b0;
					mat->quat[1] = b1;
					mat->quat[2] = b2;
					mat->quat[3] = b3;
					r0 = root->quat[0];
					r3 = root->quat[3];
					r2 = root->quat[2];
					r1 = root->quat[1];
					x = ((b0 * r3 + r0 * b3) + r1 * b2) - b1 * r2;
					y = ((b1 * r3 - r0 * b2) + r1 * b3) + b0 * r2;
					w = ((r3 * b3 - b0 * r0) - b1 * r1) - r2 * b2;
					z = ((b1 * r0 + r3 * b2) - b0 * r1) + r2 * b3;
				}
				mat->quat[0] = x;
				mat->quat[3] = w;
				mat->quat[2] = z;
				mat->quat[1] = y;
			}
			SetTransWeight(mat);
			const float *base = &model->trans[localIndex * 3];
			float k = ((unsigned int)model->noScalePartBits[wordIndex] & bit) ? 1.0f : scale;
			float tx = k * mat->trans[0] + base[0];
			float tz = k * mat->trans[2] + base[2];
			float ty = k * mat->trans[1] + base[1];
			float p0 = parent->quat[0], p1 = parent->quat[1], p2 = parent->quat[2], p3 = parent->quat[3];
			float ptw = parent->transWeight;
			float a = p1 * ptw;
			float b = p0 * ptw;
			float d = p3 * (p2 * ptw);
			float e = b * p0;
			float g = (p2 * ptw) * p2;
			mat->trans[0] = (((1.0f - (g + a * p1)) * tx + (p1 * b - d) * ty) + (p3 * a + p2 * b) * tz) + parent->trans[0];
			mat->trans[1] = (((1.0f - (g + e)) * ty + (d + p1 * b) * tx) + (p2 * a - p3 * b) * tz) + parent->trans[1];
			mat->trans[2] = (((p2 * b - p3 * a) * tx + (p2 * a + p3 * b) * ty) + (1.0f - (a * p1 + e)) * tz)
			                + parent->trans[2];
		}
	}
}
