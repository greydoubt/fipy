#!/usr/bin/env python

## -*-Pyth-*-
 # ###################################################################
 #  FiPy - Python-based finite volume PDE solver
 # 
 #  FILE: "faceTerm.py"
 #                                    created: 11/17/03 {10:29:10 AM} 
 #                                last update: 12/6/04 {4:50:29 PM} 
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
 # system.  NIST assumes no responsibility whatsever for its use by
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
 #  2003-11-17 JEG 1.0 original
 # ###################################################################
 ##
 
import Numeric

from fipy.terms.term import Term
import fipy.tools.vector
import fipy.tools.array as array
from fipy.tools.inline import inline
from fipy.tools.sparseMatrix import SparseMatrix

class FaceTerm(Term):
    def __init__(self,):
	Term.__init__(self)
	
    def getCoeffMatrix(self, mesh, weight):
	coeff = self.getCoeff(mesh)
	return {
	    'cell 1 diag': coeff * weight['cell 1 diag'],
	    'cell 1 offdiag': coeff * weight['cell 1 offdiag'],
	    'cell 2 diag': coeff * weight['cell 2 diag'],
	    'cell 2 offdiag': coeff * weight['cell 2 offdiag']
	}

    def implicitBuildMatrix(self, L, id1, id2, b, weight, mesh, boundaryConditions):
	coeffMatrix = self.getCoeffMatrix(mesh, weight)
	
	interiorFaceIDs = mesh.getInteriorFaceIDs()
	
	L.addAt(array.take(coeffMatrix['cell 1 diag'], interiorFaceIDs),    id1, id1)
	L.addAt(array.take(coeffMatrix['cell 1 offdiag'], interiorFaceIDs), id1, id2)
	L.addAt(array.take(coeffMatrix['cell 2 offdiag'], interiorFaceIDs), id2, id1)
	L.addAt(array.take(coeffMatrix['cell 2 diag'], interiorFaceIDs),    id2, id2)
	
        for boundaryCondition in boundaryConditions:
            LL,bb,ids = boundaryCondition.getContribution(coeffMatrix['cell 1 diag'], coeffMatrix['cell 1 offdiag'])
                
	    L.addAt(LL,ids,ids)
		
            fipy.tools.vector.putAdd(b, ids, bb)

    def explicitBuildMatrix(self, oldArray, id1, id2, b, weight, mesh, boundaryConditions):
	coeffMatrix = self.getCoeffMatrix(mesh, weight)

        inline.optionalInline(self._explicitBuildMatrixIn, self._explicitBuildMatrixPy, oldArray, id1, id2, b, coeffMatrix, mesh)
        
        for boundaryCondition in boundaryConditions:

            LL,bb,ids = boundaryCondition.getContribution(coeffMatrix['cell 1 diag'], coeffMatrix['cell 1 offdiag'])
            oldArrayIds = array.take(oldArray, ids)
            fipy.tools.vector.putAdd(b, ids, -LL * oldArrayIds)
            fipy.tools.vector.putAdd(b, ids, bb)

    def _explicitBuildMatrixIn(self, oldArray, id1, id2, b, weightedStencilCoeff, mesh):

	weight = self.getWeight()['explicit']
        coeff = Numeric.array(self.getCoeff())
        Nfac = mesh.getNumberOfFaces()

        cell1Diag = Numeric.resize(Numeric.array(weight['cell 1 diag']), (Nfac,))
        cell1OffDiag = Numeric.resize(Numeric.array(weight['cell 1 offdiag']), (Nfac,))
        cell2Diag = Numeric.resize(Numeric.array(weight['cell 2 diag']), (Nfac,))
        cell2OffDiag = Numeric.resize(Numeric.array(weight['cell 2 offdiag']), (Nfac,))

	inline.runInlineLoop1("""
	    long int faceID = faceIDs(i);
	    long int cellID1 = id1(i);
	    long int cellID2 = id2(i);
	    double oldArrayId1 = oldArray(cellID1);
	    double oldArrayId2 = oldArray(cellID2);
	 
	    b(cellID1) += -coeff(faceID) * (cell1Diag(faceID) * oldArrayId1 + cell1OffDiag(faceID) * oldArrayId2);
	    b(cellID2) += -coeff(faceID) * (cell2Diag(faceID) * oldArrayId2 + cell2OffDiag(faceID) * oldArrayId1);
	""",oldArray = Numeric.array(oldArray),
	    id1 = id1,
	    id2 = id2,
	    b = b,
	    cell1Diag = cell1Diag,
	    cell1OffDiag = cell1OffDiag,
	    cell2Diag = cell2Diag,
	    cell2OffDiag = cell2OffDiag,
	    coeff = coeff,
	    faceIDs = mesh.getInteriorFaceIDs(),
	    ni = len(mesh.getInteriorFaceIDs()))

    def _explicitBuildMatrixPy(self, oldArray, id1, id2, b, coeffMatrix, mesh):
        oldArrayId1, oldArrayId2 = self.getOldAdjacentValues(oldArray, id1, id2)

	interiorFaceIDs = mesh.getInteriorFaceIDs()
	
	cell1diag = array.take(coeffMatrix['cell 1 diag'], interiorFaceIDs)
	cell1offdiag = array.take(coeffMatrix['cell 1 offdiag'], interiorFaceIDs)
	cell2diag = array.take(coeffMatrix['cell 2 diag'], interiorFaceIDs)
	cell2offdiag = array.take(coeffMatrix['cell 2 offdiag'], interiorFaceIDs)
	
	fipy.tools.vector.putAdd(b, id1, -(cell1diag * oldArrayId1[:] + cell1offdiag * oldArrayId2[:]))
	fipy.tools.vector.putAdd(b, id2, -(cell2diag * oldArrayId2[:] + cell2offdiag * oldArrayId1[:]))

    def getOldAdjacentValues(self, oldArray, id1, id2):
	return array.take(oldArray, id1), array.take(oldArray, id2)

    def buildMatrix(self, var, boundaryConditions, oldArray, dt):
	"""Implicit portion considers
	"""

	mesh = var.getMesh()
	
	id1, id2 = mesh.getAdjacentCellIDs()
	id1 = array.take(id1, mesh.getInteriorFaceIDs())
	id2 = array.take(id2, mesh.getInteriorFaceIDs())
	
        N = len(oldArray)
        b = Numeric.zeros((N),'d')
        L = SparseMatrix(size = N)

	weight = self.getWeight()
	
        if weight.has_key('implicit'):
	    self.implicitBuildMatrix(L, id1, id2, b, weight['implicit'], mesh, boundaryConditions)

        if weight.has_key('explicit'):
            self.explicitBuildMatrix(oldArray, id1, id2, b, weight['explicit'], mesh, boundaryConditions)
            
        return (L, b)

