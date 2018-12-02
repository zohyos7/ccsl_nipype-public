import json, sys, os, shutil
from collections import OrderedDict
from os.path import join as opj
import os
import json
from nipype.interfaces.fsl import (BET, ExtractROI, FAST, FLIRT, ImageMaths,
                                   MCFLIRT, SliceTimer, Threshold)
from nipype.interfaces.spm import (Smooth, SliceTiming)
from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces.io import SelectFiles, DataSink
from nipype.algorithms.rapidart import ArtifactDetect
from nipype.algorithms.misc import Gunzip
from nipype import Workflow, Node
from statistics import median
from IPython.display import Image
import matplotlib.pyplot as plt
from matplotlib.image import imread

from nipype.interfaces.matlab import MatlabCommand
MatlabCommand.set_default_paths('/opt/spm12')

def preprocessing(*argu):
        
    argu=argu[0]
    json_file = argu[1]
    
    with open(json_file,'r') as jsonfile:
        info=json.load(jsonfile,object_pairs_hook = OrderedDict)
    
    subject_list = info["subject_list"]
    experiment_dir = info["experiment_dir"] 
    output_dir = 'datasink'
    working_dir = 'workingdir'
    
    task_list = info["task_list"]
    
    fwhm = [*map(int, info["fwhm"])]
    TR = float(info["TR"])
    iso_size = 4
    slice_list = [*map(int, info["slice order"])]
    
    # ExtractROI - skip dummy scans
    extract = Node(ExtractROI(t_min=int(info["dummy scans"]), t_size=-1, output_type='NIFTI'),
					name="extract")
                    
    slicetime = Node(SliceTiming(num_slices = len(slice_list),
									ref_slice = int(median(slice_list)),
                                    slice_order = slice_list,
                                    time_repetition = TR,
                                    time_acquisition = TR-(TR/len(slice_list))),
					name="slicetime")
    
    mcflirt = Node(MCFLIRT(mean_vol=True,
                            save_plots=True,
                            output_type='NIFTI'),
                	name="mcflirt")
               
    # Smooth - image smoothing
    smooth = Node(Smooth(), name="smooth")
    smooth.iterables = ("fwhm", fwhm)
    
    # Artifact Detection - determines outliers in functional images
    art = Node(ArtifactDetect(norm_threshold=2,
                                zintensity_threshold=3,
                                mask_type='spm_global',
                                parameter_source='FSL',
                                use_differences=[True, False],
                                plot_type='svg'),
                name="art")
    
    # BET - Skullstrip anatomical Image
    bet_anat = Node(BET(frac=0.5,
                        robust=True,
                        output_type='NIFTI_GZ'),
                    name="bet_anat")
                
    # FAST - Image Segmentation
    segmentation = Node(FAST(output_type='NIFTI_GZ'),
                        name="segmentation", mem_gb=4)
    
    # Select WM segmentation file from segmentation output
    def get_wm(files):
        return files[-1]
    
    # Threshold - Threshold WM probability image
    threshold = Node(Threshold(thresh=0.5,
                                args='-bin',
                                output_type='NIFTI_GZ'),
                    name="threshold")
                
    # FLIRT - pre-alignment of functional images to anatomical images
    coreg_pre = Node(FLIRT(dof=6, output_type='NIFTI_GZ'),
                	name="coreg_pre")
                 
    # FLIRT - coregistration of functional images to anatomical images with BBR
    coreg_bbr = Node(FLIRT(dof=6,
                            cost='bbr',
                            schedule=opj(os.getenv('FSLDIR'),
                                        'etc/flirtsch/bbr.sch'),
                            output_type='NIFTI_GZ'),
                    name="coreg_bbr")
    
    # Apply coregistration warp to functional images
    applywarp = Node(FLIRT(interp='spline',
                            apply_isoxfm=iso_size,
                            output_type='NIFTI'),
                    name="applywarp")
                 
    # Apply coregistration warp to mean file
    applywarp_mean = Node(FLIRT(interp='spline',
                                apply_isoxfm=iso_size,
                                output_type='NIFTI_GZ'),
                    name="applywarp_mean")
                 
    # Create a coregistration workflow
    coregwf = Workflow(name='coregwf')
    coregwf.base_dir = opj(experiment_dir, working_dir)
    
    # Connect all components of the coregistration workflow
    coregwf.connect([(bet_anat, segmentation, [('out_file', 'in_files')]),
                    (segmentation, threshold, [(('partial_volume_files', get_wm),
                                             'in_file')]),
                    (bet_anat, coreg_pre, [('out_file', 'reference')]),
                    (threshold, coreg_bbr, [('out_file', 'wm_seg')]),
                    (coreg_pre, coreg_bbr, [('out_matrix_file', 'in_matrix_file')]),
                    (coreg_bbr, applywarp, [('out_matrix_file', 'in_matrix_file')]),
                    (bet_anat, applywarp, [('out_file', 'reference')]),
                    (coreg_bbr, applywarp_mean, [('out_matrix_file', 'in_matrix_file')]),
                    (bet_anat, applywarp_mean, [('out_file', 'reference')]),
                    ])

    # Infosource - a function free node to iterate over the list of subject names
    infosource = Node(IdentityInterface(fields=['subject_id', 'task_name']),
						name="infosource")
    infosource.iterables = [('subject_id', subject_list),
                            ('task_name', task_list)]

    # SelectFiles - to grab the data (alternativ to DataGrabber)
    anat_file = opj('sub-{subject_id}', 'anat', 'sub-{subject_id}_T1w.nii.gz')
    func_file = opj('sub-{subject_id}', 'func',
                    'sub-{subject_id}_task-{task_name}_bold.nii.gz')

    templates = {'anat': anat_file,
				'func': func_file}
    selectfiles = Node(SelectFiles(templates,
                        			base_directory=info["base directory"]),
                   		name="selectfiles")

    # Datasink - creates output folder for important outputs
    datasink = Node(DataSink(base_directory=experiment_dir,
							container=output_dir),
					name="datasink")

    ## Use the following DataSink output substitutions
    substitutions = [('_subject_id_', 'sub-'),
                 ('_task_name_', '/task-'),
                 ('_fwhm_', 'fwhm-'),
                 ('_roi', ''),
                 ('_mcf', ''),
                 ('_st', ''),
                 ('_flirt', ''),
                 ('.nii_mean_reg', '_mean'),
                 ('.nii.par', '.par'),
                 ]
    subjFolders = [('fwhm-%s/' % f, 'fwhm-%s_' % f) for f in fwhm]
    substitutions.extend(subjFolders)
    datasink.inputs.substitutions = substitutions

    # Create a preprocessing workflow
    preproc = Workflow(name='preproc')
    preproc.base_dir = opj(experiment_dir, working_dir)

    # Connect all components of the preprocessing workflow
    preproc.connect([(infosource, selectfiles, [('subject_id', 'subject_id'),
                                            ('task_name', 'task_name')]),
    	             (selectfiles, extract, [('func', 'in_file')]),
        	         (extract, slicetime, [('roi_file', 'in_files')]),
            	     (slicetime, mcflirt, [('timecorrected_files', 'in_file')]),

    	             (selectfiles, coregwf, [('anat', 'bet_anat.in_file'),
        	                                 ('anat', 'coreg_bbr.reference')]),
            	     (mcflirt, coregwf, [('mean_img', 'coreg_pre.in_file'),
                	                     ('mean_img', 'coreg_bbr.in_file'),
                    	                 ('mean_img', 'applywarp_mean.in_file')]),
                 	(mcflirt, coregwf, [('out_file', 'applywarp.in_file')]),
                 	(coregwf, smooth, [('applywarp.out_file', 'in_files')]),

                 	(mcflirt, datasink, [('par_file', 'preproc.@par')]),
                	 (smooth, datasink, [('smoothed_files', 'preproc.@smooth')]),
                 	(coregwf, datasink, [('applywarp_mean.out_file', 'preproc.@mean')]),

                 	(coregwf, art, [('applywarp.out_file', 'realigned_files')]),
                	 (mcflirt, art, [('par_file', 'realignment_parameters')]),

                 	(coregwf, datasink, [('coreg_bbr.out_matrix_file', 'preproc.@mat_file'),
                    	                  ('bet_anat.out_file', 'preproc.@brain')]),
                	 (art, datasink, [('outlier_files', 'preproc.@outlier_files'),
                    	              ('plot_files', 'preproc.@plot_files')]),
                		 ])
	# Create preproc output graph# Creat # Create 
    preproc.write_graph(graph2use='colored', format='png', simple_form=True)

	# Visualize the graph
    img1 = imread(opj(preproc.base_dir, 'preproc', 'graph.png'))
    plt.imshow(img1)
    plt.xticks([]), plt.yticks([])
    plt.show()

	# Visualize the detailed graph# Visua # Visual 
    preproc.write_graph(graph2use='flat', format='png', simple_form=True)
    img2 = imread(opj(preproc.base_dir, 'preproc', 'graph_detailed.png'))
    plt.imshow(img2)
    plt.xticks([]), plt.yticks([])
    plt.show()
    
    print("Workflow all set. Check the workflow image :)")
    
    response = input('Should run the workflow? Enter yes or no :')
    
    if response == 'yes' :
        preproc.run('MultiProc', plugin_args={'n_procs': 10})
    elif response == 'no' :
        print('Exits the program since you entered no')
    else:
        raise RuntimeError('Should enter either yes or no')



if __name__ == "__main__":
    if len(sys.argv) == 1:
        raise RuntimeError('Should pass path to parameter specified json file')
        
    preprocessing(sys.argv)
