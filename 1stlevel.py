import os
from os.path import join as opj
import json
from nipype.interfaces.spm import Level1Design, EstimateModel, EstimateContrast
from nipype.algorithms.modelgen import SpecifySPMModel
from nipype.interfaces.utility import Function, IdentityInterface
from nipype.interfaces.io import SelectFiles, DataSink
from nipype import Workflow, Node
import pandas as pd

from nipype.interfaces.matlab import MatlabCommand
MatlabCommand.set_default_paths('/opt/spm12')


def contrast_generator(condition_names = []):
    if len(condition_names) == 0:
        condition_names = [str(x) for x in input('Enter names of conditions in the task (separate with spaces):  ').split(' ')]
    else: 
        pass
    cont_number = 0
    contrast_list = []
    response = 'yes'
    while response == 'yes':
        cont_number += 1
        cont = [None] * 4
        cont[0] = input('Enter the name of contrast:  ')
        cont[2] = condition_names
        cont[3] = [0] * len(condition_names)
        if '>' in cont[0]:
            if cont[0][cont[0].index(">")+2:] == 'Others':
                cont[1] = 'T'
                cont[3] = [-1/(len(condition_names)-1)]*len(condition_names) 
                for i in range(len(condition_names)):
                    if cont[0][:cont[0].index(">")-1] == condition_names[i]:
                        cont[3][i] = 1
                    else:
                        pass
            else:
                for i in range(len(condition_names)):
                    if cont[0][:cont[0].index(">")-1] == condition_names[i]:
                        cont[3][i] = 1
                    for n in range(len(condition_names)):
                        if cont[0][cont[0].index(">")+2:] == condition_names[n]:
                            cont[1] = 'T'
                            cont[3][n] = -1
                            break
        else:
            for i in range(len(condition_names)):
                if cont[0] == condition_names[i]:
                    cont[1] = 'T'
                    cont[3][i] = 1
                    break
                else:
                    pass
        
        exec('cont' + str(cont_number).zfill(2) + "=cont")
        contrast_list.append(eval('cont' + str(cont_number).zfill(2)))
        response = input('Would you like to make more contrasts? Enter yes or no: ')
    return contrast_list

def 1stlevel_analysis(condition_names, contrast_list)