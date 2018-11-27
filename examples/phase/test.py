


from fipy.tests.doctestPlus import _LateImportDocTestSuite
import fipy.tests.testProgram

def _suite():
    return _LateImportDocTestSuite(testModuleNames = (
                                       'impingement.test',
                                       'missOrientation.test',
                                   ),
                                   docTestModuleNames = (
                                       'binary',
                                       'anisotropyOLD',
                                       'anisotropy',
                                       'quaternary',
                                       'simple',
                                       'symmetry',
                                       'binaryCoupled',
                                       'polyxtal',
                                       'polyxtalCoupled'
                                   ),
                                   base = __name__)

if __name__ == '__main__':
    fipy.tests.testProgram.main(defaultTest='_suite')
