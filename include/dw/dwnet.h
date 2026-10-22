// The platform-independent boundary used by dw/dwnet.cpp and dw/dwutils.cpp.
// Names/prototypes from the PS4 server PDB and MAP, checked against Store callers.
#pragma once
class bdSocketRouter;
bdSocketRouter *dwGetSocketRouter();
void dwSanityCheckAddressHandle(int index, bdSocketRouter *router);
