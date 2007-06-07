#!/usr/bin/env python

## -*-Pyth-*-
 # ###################################################################
 #  FiPy - Python-based finite volume PDE solver
 # 
 #  FILE: "trilinosSolver.py"
 #                                    created: 11/14/03 {3:56:49 PM} 
 #                                last update: 1/3/07 {3:11:54 PM} 
 #  Author: Jonathan Guyer <guyer@nist.gov>
 #  Author: Daniel Wheeler <daniel.wheeler@nist.gov>
 #  Author: James Warren   <jwarren@nist.gov>
 #    mail: NIST
 #     www: http://www.ctcms.nist.gov/fipy/
 #  
 # ========================================================================
 # This software was developed at the National Institute of Standards
 # and Technology by employees of the Federal Government in the course
 # of their official duties.  Pursuant to title 17 Section 105 of the
 # United States Code this software is not subject to copyright
 # protection and is in the public domain.  FiPy is an experimental
 # system.  NIST assumes no responsibility whatsoever for its use by
 # other parties, and makes no guarantees, expressed or implied, about
 # its quality, reliability, or any other characteristic.  We would
 # appreciate acknowledgement if the software is used.
 # 
 # This software can be redistributed and/or modified freely
 # provided that any derivative works bear some notice that they are
 # derived from it, and any modified versions bear some notice that
 # they have been modified.
 # ========================================================================
 #  
 #  Description: 
 # 
 #  History
 # 
 #  modified   by  rev reason
 #  ---------- --- --- -----------
 #  2007-06-04 MLG 1.0 original
 # ###################################################################
 ##

__docformat__ = 'restructuredtext'

import sys

from pysparse import precon
from pysparse import itsolvers

from fipy.solvers.solver import Solver

# These imports should go into try-except blocks, to see what packages
# actually exist. Requires Epetra and EpetraExt, and one of Amesos/AztecOO
# Ideally, that'll also determine the default options?

from PyTrilinos import Epetra
from PyTrilinos import EpetraExt
from PyTrilinos import Amesos
from PyTrilinos import AztecOO
from PyTrilinos import ML
from PyTrilinos import IFPACK

import numpy

class TrilinosSolver(Solver):

    """
    This solver is an interface to most of the solvers and preconditioners available through PyTrilinos.

    """
    
    def __init__(self, tolerance=1e-10, iterations=1000, steps=None, \
                 solverPackage=Amesos, solverName="Klu",\
                 preconditioner=AztecOO.AZ_none, AztecOptions={},
                 MLOptions = {},
                 IFPACKPreconditionerType="ILU", IFPACKOptions={}):
        """
        :Parameters:
          - `tolerance`: The required error tolerance.
          - `iterations`: The maximum number of iterative steps to perform.
          - `steps`: A deprecated name for `iterations`.

          - `solverPackage`: Which of the Trilinos packages the solver 
                             is to be from.

                             Currently supported - Amesos, AztecOO
                             Default - Amesos

          - `solverName`: Which of the solvers from the package to use. 
                          Currently supported - 
                            Amesos:     'Klu', 'LAPACK'
                            AztecOO:    AztecOO.AZ_cg,
                                        AZtecOO.AZ_cg_condnum,
                                        AztecOO.AZ_gmres,
                                        AztecOO.AZ_gmres_condnum,
                                        AztecOO.AZ_cgs,
                                        AZ_tfqmr,
                                        AZ_bicgstab
                          Default - 'Klu'

          - `preconditioner`: Which of the AztecOO preconditioners to use. 
                              Supported:
                                        AztecOO.AZ_none,
                                        AztecOO.AZ_Jacobi,
                                        AztecOO.AZ_Neumann,
                                        AztecOO.AZ_ls,
                                        AztecOO.AZ_sym_GS,
                                        AztecOO.AZ_dom_decomp,
                                        'ML',
                                        'IFPACK'
                              Default - AZ_none

         - `AztecOptions`: Additional options to pass to Aztec.
                           A dictionary of {option: value} pairs. 
                           Each will be passed to AztecOO.SetAztecOption 
                           before solving. 

         - `MLOptions`: Additional options to pass to ML. A dictionary
                        of {option:value} pairs. This will be passed to
                        ML.SetParameterList.

         - `IFPACKPreconditionerType`: Which IFPACK preconditioner to use.
                                       Only applicable when preconditioner
                                       is set to "IFPACK".

         - `IFPACKOptions`: Additional options to pass to IFPACK. A 
                            dictionary of {option:value} pairs. It will
                            be passed to SetParameters() on the 
                            preconditioner object.

          For detailed information on the parameters for AztecOO, see 
          http://trilinos.sandia.gov/packages/aztecoo/AztecOOUserGuide.pdf

          For detailed information on the parameters for ML, see
          http://trilinos.sandia.gov/packages/ml/documentation.html

          For detailed information on the options for IFPACK, and for 
          a list of the available preconditioners, see
          http://trilinos.sandia.gov/packages/ifpack/IfpackUserGuide.pdf

          Notes - to use the AztecOO options, you need to have called 
                  "from PyTrilinos import AztecOO" explicity to be able
                  to pass Aztec solvers and options.

         """
                
        # Former default was MLList = {"max levels" : 4, "smoother: type" : "symmetric Gauss-Seidel", "aggregation: type" : "Uncoupled"} (parameters kept for reference for now)
                
        Solver.__init__(self, tolerance=tolerance, 
                        iterations=iterations, steps=steps)
        self.solverPackage = solverPackage
        self.solverName = solverName
        self.preconditioner = preconditioner
        self.AztecOptions = AztecOptions
        self.MLOptions = MLOptions
        self.IFPACKOptions = IFPACKOptions
        self.IFPACKPreconditionerType = IFPACKPreconditionerType
    
    def _makeTrilinosMatrix(self, L):
        """ 
        Takes in a pySparse matrix and returns an Epetra.CrsMatrix . 
        Slow, but works. Scales linearly.
        """
        Comm = Epetra.PyComm() # For now, no args, Communicator is serial
        m,n = L._getMatrix().shape 
        
        Map = Epetra.Map(m, 0, Comm)

        #A = Epetra.FECrsMatrix(Epetra.Copy, Map, n)
        #A.InsertGlobalValues(\
        #                Epetra.IntSerialDenseVector(range(0,m)),\
        #                Epetra.IntSerialDenseVector(range(0,n)),\
        #                Epetra.SerialDenseMatrix(L.getNumpyArray()))
        # Replaced with writing to/reading from matrixmarket format

        # Yeah, it's using a hardcoded filename, not good. It's a stopgap measure anyway...
        # keep the file in tmp to not need to do network stuff to access the home directory
        L._getMatrix().export_mtx("/tmp/A.mm")
        (ierr, A) = EpetraExt.MatrixMarketFileToCrsMatrix("/tmp/A.mm", Map)
        A.FillComplete()
        A.OptimizeStorage()
        return A
    
    def _solve(self, L, x, b):

        A = self._makeTrilinosMatrix(L)

        RHS = Epetra.Vector(b)
        LHS = Epetra.Vector(x)

        if self.solverPackage == Amesos:
            Factory = Amesos.Factory()
            Problem = Epetra.LinearProblem(A, LHS, RHS)
            Solver = Factory.Create(self.solverName, Problem)
            Solver.Solve()
        elif self.solverPackage == AztecOO:
            Solver = AztecOO.AztecOO(A, LHS, RHS)
            Solver.SetAztecOption(AztecOO.AZ_solver, self.solverName)
            if self.preconditioner == "ML":
                Prec = ML.MultiLevelPreconditioner(A, False)
                Prec.SetParameterList(self.MLOptions)
                Prec.ComputePreconditioner()
                Solver.SetPrecOperator(Prec)
            elif self.preconditioner == "IFPACK":
                Factory = IFPACK.Factory()
                Prec = Factory.Create(self.IFPACKPreconditionerType, A)
                Prec.SetParameters(self.IFPACKOptions)
                Prec.Initialize()
                Prec.Compute()
                Solver.SetPrecOperator(Prec)
            else:
                Solver.SetAztecOption(AztecOO.AZ_precond, self.preconditioner)
            Solver.SetAztecOption(AztecOO.AZ_output, AztecOO.AZ_warnings)
            for option, value in self.AztecOptions:
                Solver.SetAztecOption(option, value)
            Solver.Iterate(self.iterations,self.tolerance) 
        
        x = numpy.array(LHS)
