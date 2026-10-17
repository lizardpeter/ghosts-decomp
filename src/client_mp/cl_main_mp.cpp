// client_mp/cl_main_mp.cpp (Store build): the client's part of the frame.
//
// Reconstructed from the Microsoft Store build (iw6mp64_MSStore_ship), tagged with Store addresses. The server PDBs
// have no client frame; names follow Black Ops' client_mp/cl_main_mp.cpp (lineage), else sub_<VA>.
//
// The GPU sync and the mouse are done once a client frame (docs/frame.md). In game, the cgame frame does both itself,
// right before it builds the frame's command: CL_SyncGpu (cls.gpuSyncedPrevFrame) and then CL_Input -> IN_Frame
// (cls.inputUpdatedPrevFrame). sub_140316290, which runs earlier in the next Com_Frame, does whichever the last frame
// didn't do and clears both flags.

#include "client/client.h"

void R_SyncGpu(int (*WorkCallback)(unsigned long long));  // gfx_d3d/r_init.cpp
void IN_Frame();                                         // win32/win_input.cpp

extern int com_frameTime;                 // qcommon/common.cpp: Sys_Milliseconds at the start of this Com_Frame
extern int old_com_frameTime;             // com_frameTime when frame_msec was last measured
extern int unk_1442B98E0;                 // the first client frame has run (name unknown)
struct DataValidation;
extern DataValidation unk_140CFC520;      // the tamper check on clViewangles (client_mp/cl_input.cpp)
void sub_14054B4B0(int msec);             // the online services' frame (Live_Frame; name unknown)
void sub_14017A6C0(DataValidation *validation, int kind);  // re-checks part of the validated data (name unknown)
void sub_140223CE0();                     // name unknown
void sub_140191F80();                     // name unknown
void sub_14018F6C0();                     // name unknown

// Store 140316AA0 (Black Ops' CL_SyncGpu, client_mp/cl_main_mp.cpp:8303)
void CL_SyncGpu(int (*WorkCallback)(unsigned long long))
{
	cls.gpuSyncedPrevFrame = true;
	R_SyncGpu(WorkCallback);
}

// Store 140316290 (name unknown; Com_Frame calls it once a frame after the server frame, with the frame's msec and
// its length in seconds): syncs with the GPU and reads the mouse unless the last client frame did, then advances the
// client's clock (cls.realtime, cls.frametime) and frame_msec, the time the frame's command covers (1..200).
void sub_140316290(int msec, float frametime)
{
	if (unk_1442B98E0)
		sub_14054B4B0(msec);
	else
		unk_1442B98E0 = 1;
	sub_14017A6C0(&unk_140CFC520, 4);
	sub_140223CE0();
	sub_140191F80();
	if (!cls.gpuSyncedPrevFrame)
	{
		cls.gpuSyncedPrevFrame = true;
		R_SyncGpu(nullptr);
	}
	if (!cls.inputUpdatedPrevFrame)
		IN_Frame();
	cls.realtime += msec;
	frame_msec = com_frameTime - old_com_frameTime;
	cls.frametime_base = frametime;
	cls.gpuSyncedPrevFrame = false;
	cls.inputUpdatedPrevFrame = false;
	cls.frametime = msec;
	if (!frame_msec)
		frame_msec = 1;
	else if (frame_msec > 200)
		frame_msec = 200;
	old_com_frameTime = com_frameTime;
	sub_14018F6C0();
}
