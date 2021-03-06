import numpy as np
from pseudoSpec1D import Grid, Launcher, TLMLauncher, Trajectory
import random as rnd
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.gridspec import GridSpec
import pickle

#-----------------------------------------------------------
#----| Utilitaries |----------------------------------------
#-----------------------------------------------------------

def degrad(signal,mu,sigma,seed=None):
    ''' 
    Gaussian noise signal degradation

    degrad(u,mu,sigma,seed=...)

    signal  :  input signal
    mu      :  noise mean (gaussian mean)
    sigma   :  noise variance
    '''
    rnd.seed(seed)
    sig_degrad=signal.copy()
    for i in xrange(signal.size):
        sig_degrad[i]=signal[i]+rnd.gauss(mu, sigma)
    return sig_degrad

def degradTraj(traj, mu, sigma, seed=None):
    '''
    <!> replaced by Trajectory.degrad()
    '''
    return traj.degrad(mu, sigma, seed=seed)


#-----------------------------------------------------------
#----| Sampling |-------------------------------------------
#-----------------------------------------------------------

def homoSampling(grid, nObs, xlim=None):
    if not isinstance(grid, Grid):
        raise TypeError("grid <pseudoSpec>")
    if xlim:
        if np.array(xlim).shape<>(2,): raise TypeError()
        if xlim[0]>=xlim[1] or xlim[0]<grid.min() or xlim[1]>grid.max():
            raise ValueError()

    coord=[]
    if xlim:
        minCoord=xlim[0]
        maxCoord=xlim[1]
    else:
        minCoord=grid.min()
        maxCoord=grid.max()

    ObsDx=(maxCoord-minCoord)/nObs
    for j in xrange(nObs):
        coord.append(minCoord+j*ObsDx)
    return coord

def rndSampling(grid, nObs, precision=2, xlim=None, seed=None):
    if not isinstance(grid, Grid):
        raise TypeError("grid <pseudoSpec>")
    if xlim:
        if np.array(xlim).shape<>(2,): raise TypeError()
        if xlim[0]>=xlim[1] or xlim[0]<grid.min() or xlim[1]>grid.max():
            raise ValueError()

    rnd.seed(seed)
    coord=[]
    i=0
    while (i < nObs):
        if xlim:
            pick=round(rnd.random()*(xlim[1]-xlim[0]), precision)+xlim[0]
        else:
            pick=round(rnd.random()*grid.L, precision)
            if grid.centered:
                pick-=grid.L/2
        if ((not pick in coord) and (pick <=grid.max()) 
                and (pick >=grid.min()) ):
            coord.append(pick)
            i+=1
    coord.sort()
    return coord 

def removeDuplicates(coord):
    coord=list(set(coord))
    coord.sort()
    return coord 



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

def obsOp_Coord_Adj(obsValues, g, obsCoord):
    """
    Trivial static observation operator adjoint
    """
    if len(obsValues)<>len(obsCoord):
        raise ValueError()
    idxObs=g.pos2Idx(obsCoord)
    nObs=len(idxObs)
    H=np.zeros(shape=(nObs,g.N))
    for i in xrange(nObs):
        H[i, idxObs[i]]=1.
    return np.dot(H.T,obsValues)


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


    #------------------------------------------------------
    #----| Init |------------------------------------------
    #------------------------------------------------------

    def __init__(self, coord, values, obsOp=None, obsOpTLMAdj=None,
                    obsOpArgs=(), metric=None):

        if isinstance(coord, Grid):
            self.grid=coord
            self.coord=coord.x
            self.nObs=coord.N
        elif isinstance(coord, np.ndarray):
            if coord.ndim <> 1:
                raise ValueError("coord.ndim==1")
            self.coord=coord
            self.nObs=len(coord)
        elif isinstance(coord, list): 
            self.coord=np.array(coord)
            self.nObs=len(coord)
        else:
            raise TypeError(
                "coord <pseudoSpec1D.Grid | numpy.ndarray>")

        if isinstance(values, list):
            values=np.array(values)
            if len(values)<>self.nObs:
                raise ValueError()
        elif isinstance(values, np.ndarray):
            if values.ndim<>1 or len(values)<>self.nObs:
                raise ValueError()
        else:
            raise TypeError()
        self.values=values

        if not ((callable(obsOp) and callable(obsOpTLMAdj)) or 
                (obsOp==None and obsOpTLMAdj==None)):
            raise TypeError(
                                "obsOp, obsOpTLMAdj <function | None>")
        if not isinstance(obsOpArgs, tuple):
            raise TypeError("obsOpArgs <tuple>")
        self.obsOp=obsOp
        self.obsOpTLMAdj=obsOpTLMAdj
        self.obsOpArgs=obsOpArgs

        if metric==None:
            self.metric=np.eye(self.nObs)
        elif isinstance(metric, (float, int)):
            self.metric=metric*np.eye(self.nObs)
        elif isinstance(metric, np.ndarray):
            if metric.ndim==1:
                self.metric=np.diag(metric)
            elif metric.ndim==2:
                # this is why coord must not be sorted!
                self.metric=metric
            else:
                raise ValueError("metric.ndim=[1|2]")
        else:   
            raise TypeError("metric <None | numpy.ndarray>")
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
            raise TypeError("g <Grid>")
        if not isinstance(x, np.ndarray):
            raise TypeError("x <numpy.ndarray>")
        if not (x.ndim==1 or len(x)==g.N):
            raise ValueError("x.shape=(g.N)")
        if self.obsOp<>None:
            return self.obsOp(x, g, self.coord, *self.obsOpArgs)
        else:
            return x

    def modelEquivalent_Adj(self, obsValues, g):
        if not isinstance(g, Grid):
            raise TypeError("g <Grid>")
        if self.obsOpTLMAdj<>None:
            return self.obsOpTLMAdj(obsValues, g, self.coord, 
                                    *self.obsOpArgs)
        else:
            return obsValues


    #------------------------------------------------------
    
    def innovation(self, x, g):
        if not isinstance(g, Grid):
            raise TypeError("g <Grid>")
        if not isinstance(x, np.ndarray):
            raise TypeError("x <numpy.ndarray>")
        if not (x.ndim==1 or len(x)==g.N):
            raise ValueError("x.shape=(g.N)")
        return self.values-self.modelEquivalent(x, g)

    def innovation_Adj(self, d, g):
        if not isinstance(g, Grid):
            raise TypeError("g <Grid>")
        return -self.modelEquivalent_Adj(d, g)

    #------------------------------------------------------

    def interpolate(self, g):
        if not isinstance(g, Grid):
            raise TypeError("g <Grid>")
        return g.x[self.__pos2Idx(g)]


    #------------------------------------------------------
    
    def prosca(self, y1, y2):
        if len(y1)<>self.nObs or len(y2)<>self.nObs:
            raise ValueError()
        return np.dot(y1, np.dot(self.metric, y2))

    #------------------------------------------------------

    def norm(self, y):
        return np.sqrt(self.prosca(y,y))


    def modelEqNorm(self, x, g):
        return self.norm(self.modelEquivalent(x, g))
    
    #------------------------------------------------------

    def correlation(self, y):
        return self.prosca(self.values, y)/(
                self.norm(self.values)*self.norm(y))
    
    def corrModelEq(self, x, grid):
        y=self.modelEquivalent(x, grid)
        return self.correlation(y)
    
    def corrModelEqBkg(self, v, x_bkg, grid):
        inno=self.values-self.modelEquivalent(x_bkg, grid)
        Hv=self.modelEquivalent(v,grid)
        return self.prosca(Hv,inno)/(self.norm(inno)*self.norm(Hv))


    #------------------------------------------------------
    #----| I/O method |------------------------------------
    #------------------------------------------------------

    def dump(self, fun):
        pickle.dump(self.coord, fun)
        pickle.dump(self.metric, fun)
        pickle.dump(self.obsOp, fun)
        pickle.dump(self.obsOpArgs, fun)
        pickle.dump(self.obsOpTLMAdj, fun)
        pickle.dump(self.values, fun)

    #-------------------------------------------------------
    #----| Plotting methods |-------------------------------
    #-------------------------------------------------------
    
    def plot(self, values, g,  axe=None, 
                linestyle='', marker='o', **kwargs):

        if not isinstance(g, Grid):
            raise TypeError("g <Grid>")
        axe=self.__checkAxe(axe)
        axe.plot(self.interpolate(g), values, marker=marker,
                    linestyle=linestyle, **kwargs)
        return axe

    #-------------------------------------------------------

    def plotModelEquivalent(self, field, g, axe=None, 
                            linestyle='', marker='o', **kwargs):
        if not isinstance(g, Grid):
            raise TypeError("g <Grid>")
        axe=self.__checkAxe(axe)
        axe=self.plot(self.modelEquivalent(field, g), g, axe=axe, 
                            linestyle='', marker='o', **kwargs)
        return axe

    #-------------------------------------------------------

    def plotObs(self, g, continuousField=None, axe=None, marker='o',
                correlation=False, observability=False, deviation=None,
                xlim=None,   ylim=None,
                continuousFieldStyle='k-', 
                continuousFieldLabel=None,
                **kwargs):

        if not isinstance(g, Grid):
            raise TypeError("g <Grid>")
        axe=self.__checkAxe(axe)
        axe=self.plot(self.values, g, axe=axe,
                        marker=marker, linestyle='', **kwargs)
        if isinstance(continuousField, np.ndarray):
            if (continuousField.ndim==1 and 
                    len(continuousField)==g.N):
                axe.plot(g.x, continuousField, continuousFieldStyle, 
                        label=continuousFieldLabel)
                if observability or correlation:
                    text=""
                    if observability:
                        text+=(r'$\Vert x\Vert_o=%.2f$'%self.norm(
                                self.modelEquivalent(continuousField, g))
                                +'\n')
                    if correlation:
                        text+=(r'$\rho_c=%.2f$'%self.correlation(
                                self.modelEquivalent(continuousField, g))
                                +'\n')
                    axe.text(0.05,0.8, text, transform=axe.transAxes)
                if isinstance(deviation, (float, int)):
                    axe.axhline(y=deviation, linestyle=':', color='k')
                    axe.axhline(y=-deviation, linestyle=':', color='k')
            else:
                raise ValueError(
                        "incompatible continuous field dimensions")
        if xlim<>None:
            axe.set_xlim(xlim)
        if ylim<>None:
            axe.set_ylim(ylim)
        return axe

    #-------------------------------------------------------

    def plotInno(self, g, x, continuousField=None, axe=None, 
                marker='o', xlim=None,   
                continuousFieldStyle='k-', 
                continuousFieldLabel=None,
                **kwargs):

        if not isinstance(g, Grid):
            raise TypeError("g <Grid>")
        axe=self.__checkAxe(axe)
        axe=self.plot(self.innovation(x, g), g, axe=axe,
                        marker=marker, linestyle='', **kwargs)
        if isinstance(continuousField, np.ndarray):
            if (continuousField.ndim==1 and 
                    len(continuousField)==g.N):
                axe.plot(g.x, continuousField, continuousFieldStyle, 
                        label=continuousFieldLabel)
            else:
                raise ValueError(
                        "incompatible continuous field dimensions")
        if xlim<>None:
            axe.set_xlim(xlim)
        return axe



    #-------------------------------------------------------

    def __checkAxe(self, axe):
        if axe==None:
            axe=plt.subplot(111)
        elif not (isinstance(axe,(Axes, GridSpec))):
            raise TypeError(
                "axe < matplotlib.axes.Axes | matplotlib.gridspec.GridSpec >")
        return axe
    #------------------------------------------------------
    #----| Classical overloads |----------------------------
    #-------------------------------------------------------

    def __str__(self):
        output="____| StaticObs |___________________________"
        output+="\n   nObs=%d"%self.nObs
        output+="\n   coord:\n     %s\n"%self.coord.__str__()
        output+="\n   observation operator:\n     %s"%self.obsOp
        output+="\n   observation tangeant operator adjoint:"
        output+="\n     %s"%self.obsOpTLMAdj
        output+="\n____________________________________________"
        return output

    #------------------------------------------------------

    def _extendMetric(self, statObs):
        '''
        Build the observation operator metric
        assuming observation sets independant
        '''
        metric=np.zeros(shape=(self.nObs+statObs.nObs,
                              self.nObs+statObs.nObs))
        if self.nObs>0 and statObs.nObs>0:
            metric[:self.nObs, :self.nObs]=self.metric
            metric[-statObs.nObs:, -statObs.nObs:]=statObs.metric
        elif self.nObs>0 and statObs.nObs==0:
            metric=self.metric
        elif self.nObs==0:
            metric=statObs.metric 
        
        return metric

    def __add__(self, statObs, obsOpEq=True):
        if not isinstance(statObs, StaticObs): raise TypeError()
        
        if obsOpEq:
            if (self.obsOp<>statObs.obsOp or
                self.obsOpTLMAdj<>statObs.obsOpTLMAdj or
                self.obsOpArgs<>statObs.obsOpArgs):
                raise ValueError()

        metric=self._extendMetric(statObs)

        newCoord=self.coord.tolist()
        newCoord.extend(statObs.coord.tolist())

        newValues=self.values.tolist()
        newValues.extend(statObs.values.tolist())

        return StaticObs(newCoord, newValues, 
                         obsOp=self.obsOp, obsOpTLMAdj=self.obsOpTLMAdj,
                         obsOpArgs=self.obsOpArgs, metric=metric)

        
        
        
        
#=====================================================================

def loadStaticObs(fun):

    coord=pickle.load(fun)
    metric=pickle.load(fun)
    obsOp=pickle.load(fun)
    obsOpArgs=pickle.load(fun)
    obsOpTLMAdj=pickle.load(fun)
    values=pickle.load(fun)

    sObs=StaticObs(coord, values, obsOp=obsOp, obsOpTLMAdj=obsOpTLMAdj,
                    obsOpArgs=obsOpArgs, metric=metric)
    return sObs

#=====================================================================
#---------------------------------------------------------------------
#=====================================================================


class TimeWindowObs(object):
    """
    TimeWindowObs : discrete times observations class

        d_Obs       :   {time : <staticObs>} <dict>
        propagator  :   propagator launcher <Launcher>

    """


    #------------------------------------------------------
    #----| Init |------------------------------------------
    #------------------------------------------------------

    def __init__(self, d_Obs):
        
        if not isinstance(d_Obs, dict):
            raise TypeError("d_Obs <dict {time:<StaticObs>}>")
        if d_Obs.keys()==[]:
            self.empty=True
        else:
            self.empty=False
            for t in d_Obs.keys():
                if not (isinstance(t, (float,int)) 
                        and isinstance(d_Obs[t], StaticObs)):
                    raise TypeError(
                        "d_Obs <dict {time <float>: <StaticObs>}>")
                if d_Obs[t].obsOp<>d_Obs[d_Obs.keys()[0]].obsOp:
                    raise ValueError("all obsOp must be the same")


        self.times=np.array(d_Obs.keys())
        self.times.sort()

        self.nTimes=len(self.times)
        self.d_Obs=d_Obs
        self.nObs=0
        self.values={}
        if not self.empty:
            self.tMax=np.max(self.times)
            self.tMin=np.min(self.times)
            for t in self.times:
                self.nObs+=self.d_Obs[t].nObs
                self.values[t]=self.d_Obs[t].values
            self.obsOp=d_Obs[self.times[0]].obsOp
            self.obsOpArgs=d_Obs[self.times[0]].obsOpArgs
        else:
            self.tMax=None
            self.tMin=None
            self.obsOp=None
            self.obsOpArgs=()

       
                
    #------------------------------------------------------
    #----| Private methods |-------------------------------
    #------------------------------------------------------

    def __propagatorValidate(self, propagator, 
                             tlm=False, checkReference=True):
        if not tlm:
            if not isinstance(propagator, Launcher):
                raise ValueError("propagator <Launcher>")
        else:
            if not isinstance(propagator, TLMLauncher):
                raise ValueError("propagator <TLMLauncher>")
            if checkReference:
                if not propagator.isReferenced:
                    raise RuntimeError("TLM not referenced")
                
            
    #------------------------------------------------------

    def _times2NDt(self, dt, t0=0.):
        nDtList=[]
        for t in self.times:
            if t > t0:
                nDtList.append(int((t-t0)/dt))
        return nDtList

    #------------------------------------------------------
    #----| Public methods |--------------------------------
    #------------------------------------------------------
    
    def prosca(self, d_y1, d_y2):
        if d_y1.keys()<>d_y2.keys():    
            raise ValueError()
        prosca=0.
        for t in d_y1.keys():
            prosca+=self[t].prosca(d_y1[t],d_y2[t])
        return prosca
   
    #------------------------------------------------------
    
    def squareNorm(self, d_y):
        return self.prosca(d_y, d_y)
    
    #------------------------------------------------------
    
    def norm(self, d_y):
        return np.sqrt(self.prosca(d_y, d_y))

    #------------------------------------------------------

    def modelEquivalent(self, x, nlModel, t0=0.):
        if self.empty:
            raise RuntimeError()
        self.__propagatorValidate(nlModel)
        nDtList=self._times2NDt(nlModel.dt, t0=t0)
        g=nlModel.grid

        d_x=nlModel.d_nDtInt(x, nDtList, t0=t0)
        
        d_Hx={}
        for n in xrange(len(nDtList)):
            i=nDtList[n]
            t=self.times[n]
            d_Hx[t]=self.d_Obs[t].modelEquivalent(d_x[i], g)

        return d_Hx

    #------------------------------------------------------

    def modelEquivalentTLM(self, x, tlm, t0=0.):
        if self.empty:
            raise RuntimeError()
        self.__propagatorValidate(tlm, tlm=True)
        nDtList=self._times2NDt(tlm.dt, t0=t0)
        g=tlm.grid

        d_x=tlm.d_nDtInt(x, nDtList, t0=t0)
        
        d_Hx={}
        for n in xrange(len(nDtList)):
            i=nDtList[n]
            t=self.times[n]
            d_Hx[t]=self.d_Obs[t].modelEquivalent(d_x[i], g)

        return d_Hx

        
    def modelEquivalent_Adj(self, d_inno, tlm, t0=0.):
        if self.empty:
            raise RuntimeError()
        self.__propagatorValidate(tlm, tlm=True)
        nDtList=self._times2NDt(tlm.dt, t0=t0)
        g=tlm.grid

        d_w={} 
        for n in xrange(len(nDtList)):
            i=nDtList[n]
            t=self.times[n]
            d_w[i]=self.d_Obs[t].modelEquivalent_Adj(d_inno[t], g)

        adj=tlm.d_nDtIntAdj(d_w, t0=t0)

        return adj
        
    #------------------------------------------------------

    def modelEqNorm(self, x, nlModel, t0=0.):
        return self.norm(self.modelEquivalent(x, nlModel, t0=t0))

    #------------------------------------------------------
    
    def innovation(self, x, nlModel, t0=0.):
        if self.empty:
            raise RuntimeError()
        self.__propagatorValidate(nlModel)
        d_inno={}
        d_Hx=self.modelEquivalent(x, nlModel, t0=t0)
        for t in self.times:
            d_inno[t]=self.d_Obs[t].values-d_Hx[t]
        return d_inno
        
    #------------------------------------------------------

    def dump(self, fun):
        pickle.dump(self.nTimes, fun)
        pickle.dump(self.times, fun)
        for i in xrange(self.nTimes):      
            self.d_Obs[self.times[i]].dump(fun)        
    
    #------------------------------------------------------
    def cut(self, tMin=None, tMax=None):
        if tMin==None: tMin=self.tMin
        if tMax==None: tMax=self.tMax

        cut_d_Obs={}
        for t in self.d_Obs.keys():
            if t >= tMin and t<= tMax:
                cut_d_Obs[t]=self[t]
                
        return TimeWindowObs(cut_d_Obs)
    #-------------------------------------------------------
    #----| Plotting methods |-------------------------------
    #-------------------------------------------------------
    
    def plotObs(self, g, nbGraphLine=3, trajectory=None, 
                    observability=False, correlation=False, deviation=None, 
                    xlim=None, ylim=None, 
                    trajectoryStyle='k', 
                    trajectoryLabel=None,
                    **kwargs):


        if self.empty:
            raise RuntimeError()
        if not (isinstance(trajectory, Trajectory) or trajectory==None): 
            raise TypeError("trajectory <None | Trajectory>")
        if self.nTimes < nbGraphLine:
            nSubRow=self.nTimes
        else:
            nSubRow=nbGraphLine
        nSubLine=self.nTimes/nSubRow
        if self.nTimes%nSubRow: nSubLine+=1
        i=0
        axes=[]
        for t in self.times:
            axes.append(plt.subplot(nSubLine, nSubRow, i+1))
            if trajectory==None:
                self[t].plotObs(g, axe=axes[i], xlim=xlim, ylim=ylim,
                                deviation=deviation, **kwargs)
            else:
                self[t].plotObs(g, axe=axes[i], xlim=xlim, ylim=ylim, 
                                continuousField=trajectory.whereTime(t),
                                continuousFieldStyle=trajectoryStyle, 
                                continuousFieldLabel=trajectoryLabel,
                                correlation=correlation, 
                                observability=observability, 
                               deviation=deviation, **kwargs)
            axes[i].set_title("$t=%f$"%t)
            i+=1

        return axes
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

    #------------------------------------------------------

    def __add__(self, twObs):
        if not isinstance(twObs, TimeWindowObs):
            raise TypeError()

        d_Obs1=self.d_Obs.copy()
        d_Obs2=twObs.d_Obs.copy()
        new_d_Obs={}
        # check for cooccurences
        for t in d_Obs1.keys():
            if t in d_Obs2.keys():
                new_d_Obs[t]=d_Obs1.pop(t)+d_Obs2.pop(t)
        # merge the rest
        new_d_Obs.update(d_Obs1)
        new_d_Obs.update(d_Obs2)
                
        return TimeWindowObs(new_d_Obs)
#=====================================================================

def loadTWObs(fun):

    nTimes=pickle.load(fun)
    times=pickle.load(fun)
    d_Obs={}
    for i in xrange(nTimes):
        d_Obs[times[i]]=loadStaticObs(fun)

    TWObs=TimeWindowObs(d_Obs) 
    return TWObs



#=====================================================================
#---------------------------------------------------------------------
#=====================================================================

if __name__=="__main__":
    import matplotlib.pyplot as plt
    import pyKdV as kdv
    
    plotObs=False
    #----| Static obs |---------------------------    
    Ntrc=144
    g=kdv.PeriodicGrid(Ntrc)
        

    u0=kdv.rndSpecVec(g, Ntrc=10,  amp=1., seed=0)
    u0+=1.5*kdv.gauss(g.x, 40., 20. )-1.*kdv.gauss(g.x, -20., 14. )
    u0+=kdv.soliton(g.x, 0., amp=5., beta=1., gamma=-1)


    obs1=StaticObs(g, u0, None)

    obs2Coord=np.array([-50., 0., 70.])
    obs2=StaticObs(obs2Coord, u0[g.pos2Idx(obs2Coord)],
                    obsOp_Coord, obsOp_Coord_Adj)

    if plotObs:
        obs1.plotObs(g)
        obs2.plotObs(g, marker=(3,0,33), markersize=20)

    #----| TimeWindow Obs |-----------------------    
    testOpHAdj=True
    testOpHGrad=True
    tTotal=10.
    t0=4.
    tInt=tTotal-t0
    dt=0.01

    kdvParam=kdv.Param(g)
    model=kdv.kdvLauncher(kdvParam, dt=dt)

    u=model.integrate(u0, tTotal)
    
    nObs=10
    freqObs=3
    d_Obs={}
    timesObs=[i*(tTotal)/freqObs for i in xrange(1,freqObs+1)]
    for tObs in timesObs:
        coords=rndSampling(g, nObs, seed=tObs)
        d_Obs[tObs]=StaticObs(coords, 
                              u.whereTime(tObs)[g.pos2Idx(coords)],
                              obsOp_Coord, obsOp_Coord_Adj)
    twObs1=TimeWindowObs(d_Obs)

    if plotObs:
        plt.figure()
        twObs1.plotObs(g, trajectory=u)
    
    if testOpHAdj:
        #----| AD chain adjoint test |----------------
        print("\nTesting TimeWindowObs.modelEquivalent() adjoint") 
        # <y, Hx> - <H*y, x>
        tlm=kdv.kdvTLMLauncher(kdvParam)
        tlm.reference(u)

        x=kdv.rndSpecVec(g, amp=0.1, seed=1)
        y=twObs1.modelEquivalent(kdv.rndSpecVec(g, amp=0.1, seed=2),
                                    tlm, t0=t0)

        print("  1: x -( H )-> Hx ")
        Hx=twObs1.modelEquivalentTLM(x, tlm, t0=t0)
        print("  2: y -( H*)-> H*y ")
        Ay=twObs1.modelEquivalent_Adj(y, tlm, t0=t0)
        
        y_Hx=0.
        for t in y.keys():
            y_Hx+=np.dot(y[t], Hx[t])
        Ay_x=np.dot(Ay, x)
        print("    <y, Hx> - <H*y, x>=%e\n"%(y_Hx-Ay_x))
    
    if testOpHGrad:
        print("\nGradient test on |Hx|^2") 

        def fct(x, twObs, model, tlm, t0):
            Hx=twObs.modelEquivalent(x, model, t0=t0)
            J=0.5*twObs.squareNorm(Hx)
            return J

        def gradFct(x, twObs, model, tlm, t0):
            Hx=twObs.modelEquivalent(x, model, t0=t0)
            tlm.reference(model.integrate(x, twObs.times[-1], t0=t0))
            RHx={}
            for t in Hx.keys():
                RHx[t]=np.dot(twObs[t].metric, Hx[t])
            gradJ=twObs.modelEquivalent_Adj(RHx, tlm, t0=t0)
            return gradJ

        kdv.gradientTest(u0, fct, gradFct, args=(twObs1, model, tlm, t0))
