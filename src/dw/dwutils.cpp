// dw/dwutils.cpp: PS4 PDB line 440; Store 1405DA910-1405DA92E.
// The Store disassembly calls the bdNetImpl singleton accessor, returns null when
// it fails, and otherwise tail-calls bdNetImpl::getSocketRouter.
#include "dw/dwnet.h"

class bdNetImpl
{
public:
    bdSocketRouter *getSocketRouter();
};
template <typename T> class bdSingleton
{
public:
    static T *getInstance();
};

bdSocketRouter *dwGetSocketRouter()
{
    bdNetImpl *net = bdSingleton<bdNetImpl>::getInstance();
    return net ? net->getSocketRouter() : nullptr;
}
