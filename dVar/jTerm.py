import numpy as np
import scipy.optimize as sciOpt
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.gridspec import GridSpec
import pickle

def norm(x):
    return np.sqrt(np.dot(x,x))


class JMinimum(object):
    """
    Minimisation result of a JTerm
    """
    #------------------------------------------------------
    #----| Init |------------------------------------------
    #------------------------------------------------------
    def __init__(self, xOpt, fOpt, gOpt, BOpt,
                    fCalls, gCalls, 
                    warnFlag, maxiter, 
                    allvecs=None, convergence=None):
        if ((not convergence==None) and (allvecs==None)):
            raise Exception()
        self.xOpt=xOpt
        self.fOpt=fOpt
        self.gOpt=gOpt
        self.BOpt=BOpt
        self.fCalls=fCalls
        self.gCalls=gCalls
        self.warnFlag=warnFlag
        self.maxiter=maxiter
        self.allvecs=allvecs
        self.convergence=convergence

        self.gOptNorm=np.sqrt(np.dot(self.gOpt,self.gOpt))

    #------------------------------------------------------

    def dump(self, fun):
        pickle.dump(self.xOpt, fun)
        pickle.dump(self.fOpt, fun)
        pickle.dump(self.gOpt, fun)
        pickle.dump(self.BOpt, fun)
        pickle.dump(self.fCalls, fun)
        pickle.dump(self.gCalls, fun)
        pickle.dump(self.warnFlag, fun)
        pickle.dump(self.maxiter, fun)
        pickle.dump(self.allvecs, fun)
        pickle.dump(self.convergence, fun)
        
#---------------------------------------------------------------------

def loadJMinimum(fun):
    
    xOpt=pickle.load(fun)
    fOpt=pickle.load(fun)
    gOpt=pickle.load(fun)
    BOpt=pickle.load(fun)
    fCalls=pickle.load(fun)
    gCalls=pickle.load(fun)
    warnFlag=pickle.load(fun)
    maxiter=pickle.load(fun)
    allvecs=pickle.load(fun)
    convergence=pickle.load(fun)
    jMin=JMinimum(xOpt, fOpt, gOpt, BOpt,
                    fCalls, gCalls, 
                    warnFlag, maxiter, 
                    allvecs=allvecs, convergence=convergence)
    return jMin
    
#=====================================================================
#---------------------------------------------------------------------
#=====================================================================

class JTerm(object):
    """
    JTerm(costFunc, gradCostFunc, args=()) 

        costFunc, gradCostFunc(x, *args)

        <!> This is a master class not meant to be instantiated, only
            subclasses should.

        JTerms (and sub classes) can be summed :  JSum=((J1+J2)+J3)+...
        JTerms (and sub classes) can be scaled :  JMult=J1*.5
    """

    class JTermError(Exception):
        pass

    #------------------------------------------------------
    #----| Init |------------------------------------------
    #------------------------------------------------------

    def __init__(self, costFunc, gradCostFunc, 
                    args=(), maxGradNorm=None):
        
        if not (callable(costFunc) and callable(gradCostFunc)):
            raise self.JTermError("costFunc, gardCostFunc <function>")

        self._costFunc=costFunc
        self._gradCostFunc=gradCostFunc

        if not (isinstance(maxGradNorm, float) or maxGradNorm==None):
            raise self.JTermError("maxGradNorm <None|float>")
        self.maxGradNorm=maxGradNorm 
        self.args=args

        self.isMinimized=False
        self.retall=False

    #------------------------------------------------------
    #----| Public methods |--------------------------------
    #------------------------------------------------------

    def J(self, x):
        return self._costFunc(x,*self.args) 

    #------------------------------------------------------

    def gradJ(self, x):
        if self.maxGradNorm==None:
            return self._gradCostFunc(x, *self.args)
        elif isinstance(self.maxGradNorm, float):
            grad=self._gradCostFunc(x, *self.args)
            normGrad=norm(grad)
            if normGrad>self.maxGradNorm:
                grad=(grad/normGrad)*(self.maxGradNorm)
            return grad


    #------------------------------------------------------


    def minimize(self, x_fGuess, maxiter=50, retall=True,
                    testGrad=True, convergence=True, 
                    testGradMinPow=-1, testGradMaxPow=-14):

        self.retall=retall
        self.minimizer=sciOpt.fmin_bfgs

        if x_fGuess.dtype<>'float64':
            raise self.JTermError("x_fGuess.dtype=='float64'")
        #----| Gradient test |--------------------
        if testGrad:
            self.gradTest(x_fGuess,
                            powRange=[testGradMinPow, testGradMaxPow])

        #----| Minimizing |-----------------------
        minimizeReturn=self.minimizer(self.J, x_fGuess, args=self.args,
                                        fprime=self.gradJ,  
                                        maxiter=maxiter, retall=self.retall,
                                        full_output=True)

        self.createMinimum(minimizeReturn, maxiter, convergence=convergence)
        self.analysis=self.minimum.xOpt
        self.isMinimized=True

        #----| Final Gradient test |--------------
        if testGrad:
            if self.minimum.warnFlag==2:
                print("Gradient and/or function calls not changing:")
                print(" not performing final gradient test.")
            else:
                self.gradTest(self.analysis,
                            powRange=[testGradMinPow, testGradMaxPow])


    #-----------------------------------------------------

    def createMinimum(self, minimizeReturn, maxiter, convergence=True):
        if self.retall:
            allvecs=minimizeReturn[7]
            if convergence:
                convJVal=self.jAllvecs(allvecs)
        else:
            allvecs=None
            convJVal=None

        self.minimum=JMinimum(
            minimizeReturn[0], minimizeReturn[1], minimizeReturn[2],
            minimizeReturn[3], minimizeReturn[4], minimizeReturn[5],
            minimizeReturn[6], maxiter,
            allvecs=allvecs, convergence=convJVal)

    #-----------------------------------------------------

    def gradTest(self, x, output=True, powRange=[-1,-14]):
        J0=self._costFunc(x)
        gradJ0=self._gradCostFunc(x)
        n2GradJ0=np.dot(gradJ0, gradJ0)

        test={}
        for power in xrange(powRange[0],powRange[1], -1):
            eps=10.**(power)
            Jeps=self._costFunc(x-eps*gradJ0)
            
            res=((J0-Jeps)/(eps*n2GradJ0))
            test[power]=[Jeps, res]

        if output:
            print("----| Gradient test |------------------")
            print("  J0      =%+25.15f"%J0)
            print(" |grad|^2 =%+25.15f"%n2GradJ0)
            for i in  (np.sort(test.keys())[::-1]):
                print("%4d %+25.15f  %+25.15f"%(i, test[i][0], test[i][1]))

        return (J0, n2GradJ0, test)

    #------------------------------------------------------

    def plotCostFunc(self, x, epsMin=-1., epsMax=1., nDx=10, axe=None):
        axe=self._checkAxe(axe) 
        
        dx=(epsMax-epsMin)/nDx
        J=np.zeros(nDx)
        xPlusDx=np.linspace(epsMin, epsMax, nDx)
        grad=self.gradJ(x)
        for i in xrange(nDx):
            alpha=epsMin+i*dx
            J[i]=self.J(x+alpha*grad)
        axe.plot(xPlusDx,J, '^-')
        return xPlusDx, J
    #------------------------------------------------------
    #----| Private methods |-------------------------------
    #------------------------------------------------------

    def jAllvecs(self, allvecs):
        convJVal=[]
        for i in xrange(len(allvecs)):
            convJVal.append(self.J(allvecs[i]))
        return convJVal

    #------------------------------------------------------
    #----| Classical overloads |----------------------------
    #-------------------------------------------------------

    def __str__(self):
        output="////| jTerm |//////////////////////////////////////////////"
        if self.isMinimized:
            if self.warnFlag:
                output+="\n <!> Warning %d <!>"%self.warnFlag
            output+="\n function value=%f"%self.fOpt
            output+="\n gradient norm=%f"%self.gOptNorm
            output+="\n function calls=%d"%self.fCalls
            output+="\n gradient calls=%d"%self.gCalls
        else:
            output+="\n Not minimized"
        output+="\n///////////////////////////////////////////////////////////\n"
        return output

    #-------------------------------------------------------

    def __add__(self, J2):
        if not isinstance(J2, JTerm):
            raise self.JTermError("J1,J2 <JTerm>")

        def CFSum(x):
            return self.J(x)+J2.J(x)
        def gradCFSum(x):
            return self.gradJ(x)+J2.gradJ(x)

        if (self.maxGradNorm==None and J2.maxGradNorm==None):
            maxGradNorm=None
        elif self.maxGradNorm==None:
            maxGradNorm=J2.maxGradNorm
        elif J2.maxGradNorm==None:
            maxGradNorm=self.maxGradNorm


        JSum=JTerm(CFSum, gradCFSum, maxGradNorm=maxGradNorm)
        return JSum

    #------------------------------------------------------

    def __mul__(self, scalar):
        if not isinstance(scalar,float):
            raise self.JTermError("scalar <float>")

        def CFMult(x):
            return self.J(x)*scalar
        def gradCFMult(x):
            return self.gradJ(x)*scalar

        JMult=JTerm(CFMult, gradCFMult)
        return JMult
            
    
    #-------------------------------------------------------
    #----| Private plotting methods |-----------------------
    #-------------------------------------------------------

    def _checkAxe(self, axe):
        if axe==None:
            axe=plt.subplot(111)
        elif not (isinstance(axe,(Axes, GridSpec))):
            raise self.JTermError(
            "axe < matplotlib.axes.Axes | matplotlib.gridspec.GridSpec >")
        return axe

#=====================================================================
#---------------------------------------------------------------------
#=====================================================================

class TrivialJTerm(JTerm):
    
    class TrivialJTermError(Exception):
        pass


    #------------------------------------------------------
    #----| Init |------------------------------------------
    #------------------------------------------------------

    def __init__(self, maxGradNorm=None):
        if not (isinstance(maxGradNorm, float) or maxGradNorm==None):
            raise self.TrivialJTermError("maxGradNorm <None|float>")
        self.maxGradNorm=maxGradNorm 
        self.args=()
        self.isMinimized=False

    #------------------------------------------------------
    #----| Private methods |-------------------------------
    #------------------------------------------------------

    def __xValidate(self, x):
        if not isinstance(x, np.ndarray):
            raise self.TrivialJTermError("x <numpy.array>")
        if x.ndim<>1:
            raise TWObsJTermError("x.ndim==1")
    #------------------------------------------------------
    #----| Public methods |--------------------------------
    #------------------------------------------------------

    def _costFunc(self, x):
        self.__xValidate(x)
        return 0.5*np.dot(x,x) 

    #------------------------------------------------------

    def _gradCostFunc(self, x):
        self.__xValidate(x)
        return x

#=====================================================================
#---------------------------------------------------------------------
#=====================================================================


if __name__=='__main__':

    J1=TrivialJTerm()
    x=np.ones(10)
    
    print("====| Simple cost function |=======")
    print("First Guess:")
    print(x)
    J1.minimize(x)
    print("Analysis:")
    print(J1.analysis)


    J2=TrivialJTerm()
    print("\n\n====| Two terms cost function |====")
    print("First Guess:")
    print(x)
    JSum=J1+(J2*.5)
    JSum.minimize(x)
    print("Analysis:")
    print(JSum.analysis)

