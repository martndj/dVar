import numpy as np
from pseudoSpec1D import Grid, Launcher, Trajectory
import random as rnd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.gridspec import GridSpec

#-----------------------------------------------------------
#----| Utilitaries |----------------------------------------
#-----------------------------------------------------------

def degrad(signal,mu,sigma,seed=0.7349156729):
    ''' 
    Gaussian noise signal degradation

    degrad(u,mu,sigma,seed=...)

    u       :  input signal
    mu      :  noise mean (gaussian mean)
    sigma   :  noise variance
    '''
    rnd.seed(seed)
    sig_degrad=signal.copy()
    for i in xrange(signal.size):
        sig_degrad[i]=signal[i]+rnd.gauss(mu, sigma)
    return sig_degrad



#-----------------------------------------------------------
#----| Observation operators |------------------------------
#-----------------------------------------------------------

def obsOp_Coord(x, g, obsCoord):
    """
    Trivial static observation operator
    """
    idxObs=g.pos2Idx(obsCoord)
    nObs=len(idxObs)
    H=np.zeros(shape=(nObs,g.N))
    for i in xrange(nObs):
        H[i, idxObs[i]]=1.
    return np.dot(H,x)

def obsOp_Coord_Adj(obs, g, obsCoord):
    """
    Trivial static observation operator adjoint
    """
    idxObs=g.pos2Idx(obsCoord)
    nObs=len(idxObs)
    H=np.zeros(shape=(nObs,g.N))
    for i in xrange(nObs):
        H[i, idxObs[i]]=1.
    return np.dot(H.T,obs)

#=====================================================================
#---------------------------------------------------------------------
#=====================================================================

class StaticObs(object):
    """
    StaticObs class

    StaticObs(coord, values, obsOp, obsOpTLMAdj, obsOpArgs=())
        coord       :   observation positions
                            <pseudoSpec1D.Grid | numpy.ndarray>
                            (Grid for continuous observations)
        values      :   observation values <numpy.ndarray>
        obsOp       :   static observation operator <function | None>
        obsOpTLMAdj :   static observation TLM adjoint <function | None>
                            (both None when observation space = 
                             model space)
        obsOpArgs   :   obsOp additional arguments
                            obsOp(x_state, x_grid, x_obsSpaceCoord, 
                                    *obsOpArgs)
    """
    class StaticObsError(Exception):
        pass


    #------------------------------------------------------
    #----| Init |------------------------------------------
    #------------------------------------------------------

    def __init__(self, coord, values, obsOp=None, obsOpTLMAdj=None,
                    obsOpArgs=(), metric=None):

        if isinstance(coord, Grid):
            self.coordContinuous=True
            self.grid=coord
            self.coord=coord.x
            self.nObs=coord.N
        elif isinstance(coord, np.ndarray):
            if coord.ndim <> 1:
                raise self.StaticObsError("coord.ndim==1")
            self.coordContinuous=False
            order=np.argsort(coord)
            self.coord=coord[order]
            self.nObs=len(coord)
        else:
            raise self.StaticObsError(
                "coord <pseudoSpec1D.Grid | numpy.ndarray>")

        if not isinstance(values, np.ndarray):
            raise self.StaticObsError("coord <numpy.ndarray>")
        if values.ndim<>1 or len(values)<>self.nObs:
            raise self.StaticObsError("len(values)==self.nObs")
        if self.coordContinuous:
            self.values=values
        else:
            self.values=values[order]

        if not ((callable(obsOp) and callable(obsOpTLMAdj)) or 
                (obsOp==None and obsOpTLMAdj==None)):
            raise self.StaticObsError(
                                "obsOp, obsOpTLMAdj <function | None>")
        if not isinstance(obsOpArgs, tuple):
            raise self.StaticObsError("obsOpArgs <tuple>")
        self.obsOp=obsOp
        self.obsOpTLMAdj=obsOpTLMAdj
        self.obsOpArgs=obsOpArgs

        if metric==None:
            self.metric=np.eye(self.nObs)
        elif isinstance(metric, np.ndarray):
            if metric.ndim==1:
                self.metric=np.diag(metric)
            elif metric.ndom==2:
                self.metric=metric
            else:
                raise self.StaticObsError("metric.ndim=[1|2]")
        else:   
            raise self.StaticObsError("metric <None | numpy.ndarray>")
    #------------------------------------------------------
    #----| Private methods |-------------------------------
    #------------------------------------------------------

    def __pos2Idx(self, g):
        
        idx=np.zeros(self.nObs, dtype=int)
        for i in xrange(self.nObs):
            idx[i]=np.min(np.where(g.x>=self.coord[i]))
        return idx

    #------------------------------------------------------
    #----| Public methods |--------------------------------
    #------------------------------------------------------

    def modelEquivalent(self, x, g):
        if not isinstance(g, Grid):
            raise self.StaticObsError("g <Grid>")
        if not isinstance(x, np.ndarray):
            raise self.StaticObsError("x <numpy.ndarray>")
        if not (x.ndim==1 or len(x)==g.N):
            raise self.StaticObsError("x.shape=(g.N)")
        if self.obsOp<>None:
            return self.obsOp(x, g, self.coord, *self.obsOpArgs)
        else:
            return x

    #------------------------------------------------------
    
    def innovation(self, x, g):
        if not isinstance(g, Grid):
            raise self.StaticObsError("g <Grid>")
        if not isinstance(x, np.ndarray):
            raise self.StaticObsError("x <numpy.ndarray>")
        if not (x.ndim==1 or len(x)==g.N):
            raise self.StaticObsError("x.shape=(g.N)")
        return self.values-self.modelEquivalent(x, g)

    #------------------------------------------------------

    def interpolate(self, g):
        if not isinstance(g, Grid):
            raise self.StaticObsError("g <Grid>")
        return g.x[self.__pos2Idx(g)]

    #-------------------------------------------------------
    #----| Plotting methods |-------------------------------
    #-------------------------------------------------------
    
    def plot(self, g, continuousField=None, axe=None, style='go', 
                continuousFieldStyle='k-'):
        if not isinstance(g, Grid):
            raise self.StaticObsError("g <Grid>")
        axe=self.__checkAxe(axe)
        axe.plot(self.interpolate(g), self.values, style)
        if isinstance(continuousField, np.ndarray):
            if (continuousField.ndim==1 and 
                    len(continuousField)==g.N):
                axe.plot(g.x, continuousField, continuousFieldStyle)
            else:
                raise self.StaticObsError(
                        "incompatible continuous field dimensions")


    #-------------------------------------------------------

    def __checkAxe(self, axe):
        if axe==None:
            axe=plt.subplot(111)
        elif not (isinstance(axe,(Axes, GridSpec))):
            raise self.StaticObsError(
                "axe < matplotlib.axes.Axes | matplotlib.gridspec.GridSpec >")
        return axe
    #------------------------------------------------------
    #----| Classical overloads |----------------------------
    #-------------------------------------------------------

    def __str__(self):
        output="____| StaticObs |___________________________"
        if self.coordContinuous:
            output+="\n   continuous observations\n"
            output+=self.grid.__str__()
        else:
            output+="\n   discrete observations"
            output+="\n   nObs=%d"%self.nObs
            output+="\n   coord:\n     %s\n"%self.coord.__str__()
        output+="\n   observation operator:\n     %s"%self.obsOp
        output+="\n   observation tangeant operator adjoint:\n     %s"%self.obsOpTLMAdj
        output+="\n____________________________________________"
        return output




#=====================================================================
#---------------------------------------------------------------------
#=====================================================================


class TimeWindowObs(object):
    """
    TimeWindowObs : discrete times observations class

        d_Obs       :   {time : <staticObs>} <dict>
        propagator  :   propagator launcher <Launcher>

    """

    class TimeWindowObsError(Exception):
        pass


    #------------------------------------------------------
    #----| Init |------------------------------------------
    #------------------------------------------------------

    def __init__(self, d_Obs):
        
        if not isinstance(d_Obs, dict):
            raise self.TimeWindowObsError("d_Obs <dict {time:<StaticObs>}>")
        for t in d_Obs.keys():
            if not (isinstance(t, (float,int)) 
                    and isinstance(d_Obs[t], StaticObs)):
                raise self.TimeWindowObsError(
                        "d_Obs <dict {time <float>: <StaticObs>}>")
            if d_Obs[t].obsOp<>d_Obs[d_Obs.keys()[0]].obsOp:
                raise self.TimeWindowObsError("all obsOp must be the same")
        self.nTimes=len(d_Obs.keys())
        self.times=np.sort(d_Obs.keys())
        self.tMax=self.times.max()
        self.d_Obs=d_Obs
        self.nObs=0
        for t in d_Obs.keys():
            self.nObs+=self.d_Obs[t].nObs
        self.obsOp=d_Obs[d_Obs.keys()[0]].obsOp
        self.obsOpArgs=d_Obs[d_Obs.keys()[0]].obsOpArgs

                
    #------------------------------------------------------
    #----| Private methods |-------------------------------
    #------------------------------------------------------

    def __propagatorValidate(self, propagator):
        if not isinstance(propagator, Launcher):
            raise self.TimeWindowObsError("propagator <Launcher>")

    #------------------------------------------------------

    def __integrate(self, x, propagator):
        self.__propagatorValidate(propagator)
        d_xt={}
        t0=0.
        x0=x
        for t in self.times:
            if t==0.:
                d_xt[t]=x0
            else:
                d_xt[t]=(propagator.integrate(x0,t-t0)).final    
            x0=d_xt[t]
            t0=t
        
        return d_xt
    #------------------------------------------------------
    #----| Public methods |--------------------------------
    #------------------------------------------------------

    def modelEquivalent(self, x, propagator):
        self.__propagatorValidate(propagator)
        g=propagator.grid
        d_Hx={}
        d_xt=self.__integrate(x, propagator)
        for t in self.times:
            d_Hx[t]=self.d_Obs[t].modelEquivalent(d_xt[t], g)
        return d_Hx

    #------------------------------------------------------
    
    def innovation(self, x, propagator):
        self.__propagatorValidate(propagator)
        d_inno={}
        d_Hx=self.modelEquivalent(x, propagator)
        for t in self.times:
            d_inno[t]=self.d_Obs[t].values-d_Hx[t]
        return d_inno
        
    #-------------------------------------------------------
    #----| Plotting methods |-------------------------------
    #-------------------------------------------------------
    
    def plot(self, g, nbGraphLine=3, trajectory=None, style='go', 
                trajectoryStyle='k'):
        if not (isinstance(trajectory, Trajectory) or trajectory==None): 
            raise TimeWindowObsError("trajectory <None | Trajectory>")
        if self.nTimes < nbGraphLine:
            nSubRow=self.nTimes
        else:
            nSubRow=nbGraphLine
        nSubLine=self.nTimes/nSubRow
        if self.nTimes%nSubRow: nSubLine+=1
        i=0
        for t in self.times:
            i+=1
            sub=plt.subplot(nSubLine, nSubRow, i)
            if trajectory==None:
                self[t].plot(g, axe=sub, style=style)
            else:
                self[t].plot(g, axe=sub, style=style,
                                continuousField=trajectory.whereTime(t),
                                continuousFieldStyle=trajectoryStyle)
            sub.set_title("$t=%f$"%t)

    #------------------------------------------------------
    #----| Classical overloads |---------------------------
    #------------------------------------------------------

    def __getitem__(self, t):
        return self.d_Obs[t]

    #-------------------------------------------------------

    def __str__(self):
        output="====| TimeWindowObs |==========================="
        output+="\n nTimes=%d"%self.nTimes
        output+="\n %s"%self.times.__str__()
        output+="\n\n observation operator:\n  %s"%self.obsOp
        for t in self.times:
            output+="\n\n ["+str(t)+"]\n"
            output+=self.d_Obs[t].__str__()
        output+="\n================================================"
        return output


#=====================================================================
#---------------------------------------------------------------------
#=====================================================================

if __name__=="__main__":
    import matplotlib.pyplot as plt
    import pyKdV as kdv
    from pseudoSpec1D import PeriodicGrid
    
    #----| Static obs |---------------------------    
    Ntrc=100
    L=300.
    g=PeriodicGrid(Ntrc, L)
        

    x0_truth_base=kdv.rndSpecVec(g, Ntrc=10,  amp=1.)
    gaussWave=1.5*kdv.gauss(g.x, 40., 20. )-1.*kdv.gauss(g.x, -20., 14. )
    soliton=kdv.soliton(g.x, 0., amp=5., beta=1., gamma=-1)

    x0_truth=x0_truth_base+gaussWave
    x0_degrad=degrad(x0_truth, 0., 0.3)

    obs1=StaticObs(g, x0_degrad, None)

    obs2Coord=np.array([-50., 0., 70.])
    obs2=StaticObs(obs2Coord, x0_degrad[g.pos2Idx(obs2Coord)],
                    obsOp_Coord, obsOp_Coord_Adj)


    plt.subplot(211)
    plt.title("Static observations")
    plt.plot(g.x, x0_degrad, 'r', linewidth=3)
    plt.plot(g.x, x0_truth, 'k', linewidth=3)
    plt.plot(obs1.interpolate(g), obs1.values, 'g')
    plt.plot(obs1.interpolate(g), obs1.modelEquivalent(x0_truth, g), 'b')
    plt.subplot(212)
    plt.plot(g.x, x0_degrad, 'r')
    plt.plot(g.x, x0_truth, 'k', linewidth=3)
    plt.plot(obs2.interpolate(g), obs2.values, 'go')
    plt.plot(obs2.interpolate(g), obs2.modelEquivalent(x0_truth, g), 'bo')

    #----| time window obs |----------------------
    kdvParam=kdv.Param(g, beta=1., gamma=-1.)
    tInt=10.
    
    model=kdv.kdvLauncher(kdvParam, maxA=5.)
    x_truth=model.integrate(x0_truth, tInt)
    x_degrad=model.integrate(x0_degrad, tInt)

    nObsTime=3
    d_Obs1={}
    for i in xrange(nObsTime):
        d_Obs1[tInt*(i+1)/nObsTime]=StaticObs(g,
            x_degrad.whereTime(tInt*(i+1)/nObsTime), None)
    timeObs1=TimeWindowObs(d_Obs1)

    d_Obs2={}
    for i in xrange(nObsTime):
        t=tInt*(i+1)/nObsTime
        captorPosition=-80.+20.*t
        obsCoord=captorPosition+np.array([-10.,-5.,0.,5.,10.])
        obsValues=x_degrad.whereTime(t)[g.pos2Idx(obsCoord)]
        d_Obs2[t]=StaticObs(obsCoord,obsValues,
                            obsOp_Coord, obsOp_Coord_Adj)
    timeObs2=TimeWindowObs(d_Obs2)


    plt.figure()
    i=0
    for t in timeObs1.times:
        i+=1
        sub=plt.subplot(nObsTime, 1, i)
        sub.plot(g.x, x_truth.whereTime(t), 'k', linewidth=2.5)
        sub.plot(g.x, x_degrad.whereTime(t), 'r', linewidth=2.5)
        sub.plot(timeObs1[t].interpolate(g), timeObs1[t].values, 'g')
        sub.set_title("t=%.2f"%t)

    plt.figure()
    i=0
    for t in timeObs2.times:
        i+=1
        sub=plt.subplot(nObsTime, 1, i)
        sub.plot(g.x, x_truth.whereTime(t), 'k', linewidth=2.5)
        sub.plot(g.x, x_degrad.whereTime(t), 'r')
        sub.plot(timeObs2[t].interpolate(g), timeObs2[t].values, 'go')
        sub.set_title("t=%.2f"%t)
    plt.show()