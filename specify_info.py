import json, sys, os
from collections import OrderedDict

def configure_preproc_params(json_name, subject_list = None, slice_order = None):
        
    if subject_list is None:
        subject_list = []
    if slice_order is None:
        slice_order = []
    
    info = OrderedDict()
    subject_list
    
    if len(subject_list) == 0 and len(slice_order) == 0 :
        subject_list = input('You did not pass subject list & Slice order as argument. Enter the list of subjects and slice order manually \n Enter list of subject IDs whose data will be analyzed (separate with spaces ) : ')
        slice_order = input('Enter slice order of functional images for SPM slice timing(enter list object) : ')    
        
        info['subject_list'] = [str(x) for x in subject_list.split(' ')]
        info['slice order'] = [str(x) for x in slice_order.split(' ')]
        
    elif len(subject_list) > 0 and len(slice_order) == 0 :        
        slice_order = input('Got subject info, but you did not pass slice order as argument. \n Enter slice order of functional images for SPM slice timing(enter list object) : ')
        info['slice order'] = [str(x) for x in slice_order.split(' ')]
        
    elif len(subject_list) > 0 and len(slice_order) > 0 :
        info['subject_list'] = subject_list
        info['slice order'] = slice_order
    
    else:
        pass

    info['experiment_dir'] = input('Got subject info & slice order. \n Enter path to save the analyzed data: ')
    info['task_list'] = [str(x) for x in input('Enter names of tasks to preprocess the data (separate with spaces): ').split(' ')]
    info['fwhm'] = [str(x) for x in input('Enter smoothing widths to apply (separate with spaces): ').split(' ')]
    info['TR'] = input('Enter TR of functional images: ')
    info['dummy scans'] = input('Enter the number of dummy scans to drop: ')
    info['base directory'] = input('Enter the base directory where functional data will be grabbed from: ')
    
    print("** Done!\nWriting to %s **" % json_name)
    
    with open(json_name,'w') as jsonfile:
        json.dump(info,jsonfile,indent=4)
        