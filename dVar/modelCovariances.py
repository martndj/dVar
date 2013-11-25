import numpy as np
from canonicalInjection import *
from spectralLib import *

def gauss(x, x0, sig):
    return np.exp(-((x-x0)**2)/(2*sig**2))


def fCorr_isoHomo(g, sig, x0=0.):
    return gauss(g.x, x0, sig)

def rCTilde_sqrt_isoHomo(g, fCorr):
    """
    Transform of the square root correlation matrix
        (homogeneous and isotropic, in 'r' representation - see 
         canonicalInjection.py)


    Diagonal representation

        [c_0, c_1.real, c_1.imag, c_2.real, c_2.imag, ...]

        <!> It is still a second order tensor and applications on it
            must be done accordingly: LCL* (not LC).
            Following manipulation reflect that.

    """
    rFTilde=g.N*c2r(np.fft.fft(fCorr))

    rCTilde=np.zeros(g.N)
    rCTilde[0]=np.abs(rFTilde[0])
    for i in xrange(1, (g.N-1)/2+1):
        # rFTilde[idx pairs] contain real coefficients
        # resulting from c2r.C.(c2r)*
        rCTilde[2*i-1]=np.abs(rFTilde[2*i-1])
        rCTilde[2*i]=np.abs(rFTilde[2*i-1])
    
    if rCTilde.min()<0.:
        raise Exception(
        "rCTilde<0: square root complex => saddle point => big problem!")
    rCTilde_sqrt=np.sqrt(rCTilde)
    return rCTilde_sqrt


def ifft_Adj(x):
    N=len(x)
    xi=np.zeros(N)
    xi=np.fft.fft(x)
    xi=xi/N
    return xi

def B_sqrt_isoHomo_op(xi, var, rCTilde_sqrt, aliasing=3):
    """
        B_{1/2} operator

        var             :   1D array of variances
                            (diagonal os Sigma matrix)
        rCTilde_sqrt    :   1D array of the diagonal
                            of CTilde_sqrt (in 'r' basis)
    """
    Ntrc=(len(xi)-1)/3

    xiR=rCTilde_sqrt*xi         #   1
    xiC=r2c(xiR)                #   2
    x1=np.fft.ifft(xiC).real    #   3
    x2=x1*var                   #   4
    return specFilt(x2, Ntrc)   #   5


def B_sqrt_isoHomo_op_Adj(x, var, rCTilde_sqrt, aliasing=3):
    Ntrc=(len(x)-1)/3

    x2=specFilt(x, Ntrc)        #   5.T
    x1=x2*var                   #   4.T
    xiC=ifft_Adj(x1)            #   3.T
    xiR=r2c_Adj(xiC)            #   2.T
    return rCTilde_sqrt*xiR     #   1.T

def B_isoHomo_op(x, var, rCTilde_sqrt):
    return B_sqrt_isoHomo_op(B_sqrt_isoHomo_op_Adj(x, var, rCTilde_sqrt),
                        var, rCTilde_sqrt)


if __name__=='__main__':
    import random as rnd
    import matplotlib.pyplot as plt
    from pseudoSpec1D import PeriodicGrid
    rnd.seed(0.4573216806)
    
    N=11
    mu=1.
    sigRnd=1.
    
    
    
    x=np.empty(N, dtype='complex')
    y=np.empty(N)
    
    x[0]=rnd.gauss(mu, sigRnd)
    for i in xrange(1,(N-1)/2+1):
        x[i]=rnd.gauss(mu, sigRnd)+1j*rnd.gauss(mu,sigRnd)
        x[N-i]=x[i].real-1j*x[i].imag
    for i in xrange(N):
        y[i]=rnd.gauss(mu, sigRnd)
    
    print("Testing adjoint of r2c()")
    print(np.dot(x.conj(), r2c(y))-np.dot(r2c_Adj(x),y))
    
    print("Testing adjoint of ifft()")
    Lx_y=np.dot(np.fft.ifft(x), y.conj())
    x_LAdjy=np.dot(x, ifft_Adj(y).conj())
    print(Lx_y-x_LAdjy)



    Ng=100
    g=PeriodicGrid(Ng, 100., aliasing=1)
    
    
    sig=5.
    lCorr=5.
    variances=sig*np.ones(g.N)
    fCorr=fCorr_isoHomo(g, lCorr)
    CTilde_sqrt=rCTilde_sqrt_isoHomo(g, fCorr)
    
    
    # adjoint test
    rnd.seed(0.4573216806)
    mu=0.; sigNoise=2.
    xNoise=np.zeros(g.N)
    yNoise=np.zeros(g.N)
    for i in xrange(g.N):
        yNoise[i]=rnd.gauss(mu, sigNoise)
        xNoise[i]=rnd.gauss(mu, sigNoise)
    testDirect=np.dot(xNoise,
                        B_sqrt_isoHomo_op(yNoise, variances, CTilde_sqrt).conj())
    testAdjoint=np.dot(B_sqrt_isoHomo_op_Adj(xNoise, variances, CTilde_sqrt),
                        yNoise.conj())
    
    print("Adjoint test with noise: <x,Gy>-<G*x,y>")
    print(testDirect-testAdjoint)
    
    # correlation test
    xDirac=np.zeros(g.N)
    NDirac=Ng/4
    xDirac[NDirac]=1.
    x0Dirac=g.x[NDirac]
    xTest=B_isoHomo_op(xDirac, variances, CTilde_sqrt)
        

    plt.figure()
    plt.subplot(211)
    plt.plot(g.x, xTest, 'b')
    plt.plot(g.x, sig**2*fCorr_isoHomo(g, lCorr, x0Dirac), 'g')
    plt.legend([r'$ B(\delta(x-x_0))$', r'$\sigma^2f_{corr}(x-x_0)$'],
                loc='best')
    plt.title(r'$\sigma=%.1f$'%sig)
    plt.subplot(212)
    plt.plot(g.x, xTest-sig**2*fCorr_isoHomo(g, lCorr, x0Dirac), 'r')
    plt.show()
