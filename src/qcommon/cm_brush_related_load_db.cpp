// qcommon/cm_brush_related_load_db.h (Store build): the zone loaders of the brushes inside physics collision maps.
//
// Generated loader functions of qcommon/cm_brush_related_load_db.h, included into database/db_load.cpp
// (db_load.obj in the PS4/xb3 servers, whose PDBs give names and lines). Only the chain a PhysCollmap's
// BrushWrapper goes through is here; the clip map's own brush loaders (Load_cbrush_t, Load_cbrushside_t, ...) are
// the map geometry's. The code is the Store build's, tagged with Store addresses; the statements are the servers'.

#include "physics/physpreset.h"
#include "database/db_stream_api.h"

// Store 14034AF80 (qcommon/cm_brush_related_load_db.h:1463 in the PS4 PDB)
void Load_BrushWrapper(bool atStreamStart)
{
	Load_Stream(atStreamStart, varBrushWrapper, sizeof(BrushWrapper));
	varcbrushWrapper_t = &varBrushWrapper->brush;
	Load_cbrushWrapper_t(false);
	if (!varBrushWrapper->planes)
		return;
	if ((unsigned long long)varBrushWrapper->planes == DB_PTR_FOLLOWING)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		varBrushWrapper->planes = (cplane_s *)g_streamPos;
		varcplane_t = (cplane_s *)g_streamPos;
		Load_Stream(true, g_streamPos, sizeof(cplane_s) * (unsigned long long)varBrushWrapper->brush.numsides);
		return;
	}
	DB_ConvertOffsetToPointer((unsigned long long *)&varBrushWrapper->planes);
}

// Store 14035F860 (qcommon/cm_brush_related_load_db.h:1277 in the PS4 PDB)
void Load_cbrushWrapper_t(bool atStreamStart)
{
	Load_Stream(atStreamStart, varcbrushWrapper_t, sizeof(cbrush_t));
	if (varcbrushWrapper_t->sides)
	{
		g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
		varcbrushWrapper_t->sides = (cbrushside_t *)g_streamPos;
		varcbrushside_t = (cbrushside_t *)g_streamPos;
		Load_cbrushside_tArray(true, varcbrushWrapper_t->numsides);
	}
	if (varcbrushWrapper_t->baseAdjacentSide)
	{
		varcbrushWrapper_t->baseAdjacentSide = g_streamPos;
		varcbrushedge_t = g_streamPos;
		Load_Stream(true, g_streamPos, (long long)varBrushWrapper->totalEdgeCount);
	}
}

// Store 14035FA50 (qcommon/cm_brush_related_load_db.h:821 in the PS4 PDB)
void Load_cbrushside_tArray(bool atStreamStart, unsigned long long count)
{
	Load_Stream(atStreamStart, varcbrushside_t, sizeof(cbrushside_t) * count);
	cbrushside_t *side = varcbrushside_t;
	for (; count; count--)
	{
		varcbrushside_t = side;
		Load_Stream(false, side, sizeof(cbrushside_t));
		if (varcbrushside_t->plane)
		{
			if ((unsigned long long)varcbrushside_t->plane == DB_PTR_FOLLOWING)
			{
				g_streamPos = (unsigned char *)(((unsigned long long)g_streamPos + 3) & ~3ull);
				varcbrushside_t->plane = (cplane_s *)g_streamPos;
				varcplane_t = (cplane_s *)g_streamPos;
				Load_Stream(true, g_streamPos, sizeof(cplane_s));
			}
			else
			{
				DB_ConvertOffsetToPointer((unsigned long long *)varcbrushside_t);
			}
		}
		side++;
	}
}
