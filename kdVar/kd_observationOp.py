import numpy as np
import pyKdV as kdv
from dVar import pos2Idx, B_sqrt_op

class obsTimeOpError(Exception):
    pass

#-----------------------------------------------------------

def whereTrajTime(u, time):
    return np.where(u.time>=time)[0].min()

#-----------------------------------------------------------

def kd_departure(xi, x_b, var, B_sqrt_op, H, H_TL, argsH, dObs,
                    rCTilde_sqrt):
    """

        H       :   non-linear observation operator
        H_TL    :   tangent linear observation operator
    """
    
    if not (isinstance(dObs, dict)): 
        raise obsTimeOpError("dObs <dict>")
    for t in dObs.iterkeys():
        if not isinstance(dObs[t], np.ndarray):
            raise obsTimeOpError("dObs[t] <numpy.ndarray>")

    x=B_sqrt_op(xi, var, rCTilde_sqrt)+x_b[0]
    dHx_b=H(x_b[0], *argsH)
    dH_TLx=H_TL(x-x_b[0], x_b, *argsH)

    dDeparture={}
    for t in dHx_b.keys():
        dDeparture[t]=dObs[t]-dHx_b[t]-dH_TLx[t]

    return dDeparture

#-----------------------------------------------------------

def kd_opObs(x, g,  dObs, H_op, kdvParam, maxA):
    """
        Non-linear observation operator

        x       :   state <numpy.ndarray>
        g       :   <SpectralGrid>
        dObs    :   {time <float>   :   idxObs <np.array>, ...} <dict>
        H_op    :   static observation operator
    """
    if not (isinstance(dObs, dict)): 
        raise obsTimeOpError("dObs <dict>")
    for t in dObs.iterkeys():
        if not isinstance(dObs[t], np.ndarray):
            raise obsTimeOpError("dObs[t] <numpy.ndarray>")

    #----| Model equivalent |-----------
    HMx={}
    for t in np.sort(dObs.keys()):
        # parallelize this?
        tLauncher=kdv.Launcher(kdvParam, x)
        traj=tLauncher.integrate(t, maxA)
        HMx[t]=H_op(traj.final(), g, pos2Idx(g, dObs[t]))

    return HMx


#-----------------------------------------------------------

def kd_opObs_TL(dx, traj_bkg, g,  dObsPos, H_op, kdvParam, maxA):
    """
        tangent linear observation operator

        dx      :   state increment <numpy.ndarray>
        g       :   <SpectralGrid>
        dObsPos :   {time <float>   :   idxObs <np.array>, ...} <dict>
        H_op    :   static observation operator
    """
    if not (isinstance(dObsPos, dict)): 
        raise obsTimeOpError("dObsPos <dict>")
    for t in dObsPos.iterkeys():
        if not isinstance(dObsPos[t], np.ndarray):
            raise obsTimeOpError("dObsPos[t] <numpy.ndarray>")

    #----| Model equivalent |-----------
    #tInt=np.max(dObsPos.keys())
    #launcher_bkg=kdv.Launcher(kdvParam, x_bkg)
    #traj_bkg=launcher_bkg.integrate(tInt, maxA)
    HMdx={}
    t_pre=0.
    dx_pre=dx
    for t in np.sort(dObsPos.keys()):
        tLauncher=kdv.TLMLauncher(kdvParam, traj_bkg, dx_pre)
        dx_t=tLauncher.integrate(tInt=t-t_pre, t0=t_pre)
        HMdx[t]=H_op(dx_t, g, pos2Idx(g, dObsPos[t]))
        t_pre=t
        dx_pre=dx_t
    return HMdx
 
#-----------------------------------------------------------


def kd_opObs_TL_T(dObs, traj_bkg, g, dObsPos, H_op_T, kdvParam, maxA):
    """
        adjoint of tangent linear observation operator

        traj_bkg   :   background trajectory <numpy.ndarray>
        g       :   <SpectralGrid>
        dObsPos :   {time <float>   :   idxObs <np.array>, ...} <dict>
        H_op    :   static observation operator
    """
    if not (isinstance(dObsPos, dict)): 
        raise obsTimeOpError("dObsPos <dict>")
    for t in dObsPos.iterkeys():
        if not isinstance(dObsPos[t], np.ndarray):
            raise obsTimeOpError("dObsPos[t] <numpy.ndarray>")

    #----| Model equivalent |-----------
    tOrder=np.argsort(dObsPos.keys())
    #tInt=dObsPos.keys()[tOrder[-1]]
    nTime=len(tOrder)

    #launcher_bkg=kdv.Launcher(kdvParam, x_bkg)
    #traj_bkg=launcher_bkg.integrate(tInt, maxA)
    i=0
    M_TH_TObs=np.zeros(traj_bkg.grid.N)
    for t in np.sort(dObsPos.keys())[::-1]:
        i+=1
        if i<nTime:
            t_pre=dObsPos.keys()[tOrder[-1-i]]
        else:
            t_pre=0.
        print(t, t_pre, t-t_pre)
        dx=H_op_T(dObs[t], g, pos2Idx(g, dObsPos[t]))
        
        tLauncher=kdv.TLMLauncher(kdvParam, traj_bkg, dx+M_TH_TObs)
        M_TH_TObs=tLauncher.adjoint(tInt=t-t_pre, t0=t_pre)
        dx=M_TH_TObs
        
    return M_TH_TObs
 
#-----------------------------------------------------------
def kd_opObs_TL_nonSequential(dx, x_bkg, g,  dObs, H_op, kdvParam, maxA):
    """
        tangent linear observation operator

        dx      :   state increment <numpy.ndarray>
        x_bkg   :   background state <numpy.ndarray>
        g       :   <SpectralGrid>
        dObs    :   {time <float>   :   idxObs <np.array>, ...} <dict>
        H_op    :   static observation operator
    """
    if not (isinstance(dObs, dict)): 
        raise obsTimeOpError("dObs <dict>")
    for t in dObs.iterkeys():
        if not isinstance(dObs[t], np.ndarray):
            raise obsTimeOpError("dObs[t] <numpy.ndarray>")

    #----| Model equivalent |-----------
    tInt=np.max(dObs.keys())
    launcher_bkg=kdv.Launcher(kdvParam, x_bkg)
    traj_bkg=launcher_bkg.integrate(tInt, maxA)
    HMdx={}
    for t in dObs.iterkeys():
        # parallelize this?
        tLauncher=kdv.TLMLauncher(kdvParam, traj_bkg, dx)
        dx_t=tLauncher.integrate(t)
        HMdx[t]=H_op(dx_t, g, pos2Idx(g, dObs[t]))

    return HMdx
 

#===========================================================
if __name__=="__main__":
    import matplotlib.pyplot as plt
    from dVar import pos2Idx, fCorr_isoHomo, degrad, B_sqrt_op, \
                        rCTilde_sqrt_isoHomo, opObs_Idx, opObs_Idx_T
    import pyKdV as kdv
    
    
    Ntrc=100
    L=300.
    g=kdv.SpectralGrid(Ntrc, L)
        
    kdvParam=kdv.Param(g, beta=1., gamma=-1.)
    tInt=10.
    maxA=5.
    
    x0_truth_base=kdv.rndFiltVec(g, Ntrc=g.Ntrc/5,  amp=1.)
    wave=kdv.soliton(g.x, 0., amp=5., beta=1., gamma=-1)\
                +1.5*kdv.gauss(g.x, 40., 20. )-1.*kdv.gauss(g.x, -20., 14. )
    x0_truth=x0_truth_base+wave
    launcher_truth=kdv.Launcher(kdvParam, x0_truth)
    x_truth=launcher_truth.integrate(tInt, maxA)
    
    x0_bkg=x0_truth_base
    launcher_bkg=kdv.Launcher(kdvParam, x0_bkg)
    x_bkg=launcher_bkg.integrate(tInt, maxA)
    
    #----| Observations |---------
    dObsPos={}
    dObsPos[1.]=np.array([-30.,  70.])
    dObsPos[3.]=np.array([-120., -34., -20., 2.,  80., 144.])
    dObsPos[6.]=np.array([-90., -85, 4., 10.])
    dObsPos[9.]=np.array([-50., 0., 50.])
    
    H=kd_opObs
    H_TL=kd_opObs_TL
    H_TL_T=kd_opObs_TL_T
    argsH=(g, dObsPos, opObs_Idx, kdvParam, maxA)
    argsH_T=(g, dObsPos, opObs_Idx_T, kdvParam, maxA)
    
    sigR=.5
    x0_degrad=degrad(x0_truth, 0., sigR)                   
    dObs_degrad=H(x0_degrad, *argsH) 
    dObs_truth=H(x0_truth, *argsH) 
                         
    
    dR_inv={}
    for t in dObsPos.keys():
        dR_inv[t]=sigR**(-1)*np.eye(len(dObsPos[t]))
    
    #----| Preconditionning |-----
    Lc=10.
    sig=0.4
    corr=fCorr_isoHomo(g, Lc)
    rCTilde_sqrt=rCTilde_sqrt_isoHomo(g, corr)
    var=sig*np.ones(g.N)
    xi=np.zeros(g.N)
    
    #----| Departures |-----------
    dDepartures=kd_departure(xi, x_bkg, var, B_sqrt_op, H, H_TL, argsH, 
                                dObs_degrad, rCTilde_sqrt)
    for t in np.sort(dObs_degrad.keys()):
        print("t=%f"%t)
        print(dDepartures[t])
    
    #----| Validating adjoint |---
    x_rnd=kdv.rndFiltVec(g,Ntrc=g.Ntrc/4, amp=0.5)
    dY=dObs_degrad
    Hx=H_TL(x_rnd, x_bkg, *argsH)
    H_Ty=H_TL_T(dY, x_bkg, *argsH_T)
    prod1=0.
    for t in Hx.keys():
        prod1+=np.dot(dY[t], Hx[t])
    prod2=np.dot(H_Ty, x_rnd)
    print(np.abs(prod1-prod2))
        
    
    #----| Post-processing |------
    nTime=len(dObs_degrad.keys())
    plt.figure(figsize=(10.,3.*nTime))
    i=0
    for t in np.sort(dObs_degrad.keys()):
        i+=1
        sub=plt.subplot(nTime, 1, i)
        ti=whereTrajTime(x_truth, t)
        sub.plot(g.x, x_truth[ti], 'g')
        sub.plot(g.x[pos2Idx(g, dObsPos[t])], dObs_truth[t], 'go')
        sub.plot(g.x[pos2Idx(g, dObsPos[t])], dObs_degrad[t], 'ro')
        sub.plot(g.x, x_bkg[ti], 'b')
        sub.plot(g.x[pos2Idx(g, dObsPos[t])], 
                    x_bkg[ti][pos2Idx(g, dObsPos[t])], 'bo')
        sub.set_title("$t=%f$"%t)
        if i==nTime:
            sub.legend(["$x_{t}$", "$H(x_{t})$", "$y$", "$x_b$", 
                        "$H(x_b)$"], loc="lower left")
    #plt.show()    