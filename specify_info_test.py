import json, sys, os
from collections import OrderedDict
from ast import literal_eval

def configure_nipype_params(*argu):
 
    argu=argu[0]
    json_name = argu[1]

    info = OrderedDict()
    info['subject_list'] = [str(x) for x in input('Enter list of subject IDs whose data will be analyzed *enter list object* : ').split(' ')]
    info['experiment_dir'] = input('Enter path to save the analyzed data: ')
    info['task_list'] = [str(x) for x in input('Enter names of tasks to preprocess the data: ').split(' ')]
    info['fwhm'] = [str(x) for x in input('Enter smoothing widths to apply: ').split(' ')]
    info['TR'] = input('Enter TR of functional images: ')
    info['slice order'] = [str(x) for x in input('Enter slice order of functional images(for SPM slice timing)*enter list_object* : ').split(' ')]
    info['dummy scans'] = input('Enter the number of dummy scans to drop: ')
    info['base directory'] = input('Enter the base directory where functional data will be grabbed from: ')

    print("Done!\nWriting to %s.json." % json_name)
    
    with open(json_name,'w') as jsonfile:
        json.dump(info,jsonfile,indent=4)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        raise RuntimeError('Should pass path to save json_file + json_file name.')
        
    configure_nipype_params(sys.argv)
