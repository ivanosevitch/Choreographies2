import os
from re import T

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys,argparse
import random
import numpy as np
import math as m
import scipy.optimize as opt
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.colors import cnames
from matplotlib import animation
import copy
import shutil
import time
import builtins

import inspect

from Choreo_funs import *


def Find_Choreo(
    nbody,
    n_reconverge_it_max,
    ncoeff_init,
    mass,
    Sym_list,
    MomConsImposed,
    n_grad_change,
    store_folder,
    nTf,
    nbs,
    nbf,
    mass_mul,
    all_coeffs_slow_load,
    all_coeffs_fast_load_list,
    Rotate_fast_with_slow,
    Optimize_Init,
    Randomize_Fast_Init,
    mul_loops,
    save_init,
    Save_img,
    Save_thumb,
    nint_plot_img,
    img_size,
    thumb_size,
    color,
    Save_Newton_Error,
    gradtol_list,
    inner_maxiter_list,
    maxiter_list,
    outer_k_list,
    store_outer_Av_list,
    n_optim_param,
    krylov_method,
    Use_exact_Jacobian,
    disp_scipy_opt,
    line_search,
    Check_Escape,
    Look_for_duplicates,
    duplicate_eps,
    foundsol_tol,
    gradtol_max,
    Newt_err_norm_max,
    Newt_err_norm_max_save,
    Save_anim,
    nint_plot_anim,
    nperiod_anim,
    Plot_trace_anim,
    vid_size,
    n_opt_max,
    freq_erase_dict,
    coeff_ampl_o,
    k_infl,
    k_max,
    coeff_ampl_min,
    LookForTarget,
    dnint,
    file_basename,
    max_norm_on_entry,
    ):
    
    print('Searching periodic solutions of {:d} bodies'.format(nbody))

    print('Processing symmetries for {0:d} convergence levels'.format(n_reconverge_it_max+1))
    callfun = setup_changevar(nbody,ncoeff_init,mass,n_reconverge_it_max,Sym_list=Sym_list,MomCons=MomConsImposed,n_grad_change=n_grad_change)

    print('')

    args = callfun[0]

    nloop = args['nloop']
    loopnb = args['loopnb']
    loopnbi = args['loopnbi']
    nbi_tot = 0
    for il in range(nloop):
        for ilp in range(il+1,nloop):
            nbi_tot += loopnb[il]*loopnb[ilp]
        nbi_tot += loopnbi[il]
    nbi_naive = (nbody*(nbody-1))//2

    print('Imposed constraints lead to the detection of :')
    print('    {:d} independant loops'.format(nloop))
    print('    {0:d} binary interactions'.format(nbi_tot))
    print('    ==> reduction of {0:f} % wrt the {1:d} naive binary iteractions'.format(100*(1-nbi_tot/nbi_naive),nbi_naive))
    print('')

            
    

    # for i in range(n_reconverge_it_max+1):
    for i in [0]:
        
        args = callfun[0]
        print('Convergence attempt number : ',i+1)
        print('    Number of Fourier coeffs : ',args['ncoeff_list'][i])
        print('    Number of scalar parameters before constraints : ',args['coeff_to_param_list'][i].shape[1])
        print('    Number of scalar parameters after  constraints : ',args['coeff_to_param_list'][i].shape[0])
        print('    Reduction of ',100*(1-args['coeff_to_param_list'][i].shape[0]/args['coeff_to_param_list'][i].shape[1]),' %')
        print('')


    x0 = np.random.random(callfun[0]['param_to_coeff_list'][0].shape[1])
    xmin = Compute_MinDist(x0,callfun)
    if (xmin < 1e-5):
        print(xmin)
        raise ValueError("Init inter body distance too low. There is something wrong with constraints")

    # filehandler = open(store_folder+'/callfun_list.pkl',"wb")
    # pickle.dump(callfun_list,filehandler)

    callfun[0]["current_cvg_lvl"] = 0
    ncoeff = callfun[0]["ncoeff_list"][callfun[0]["current_cvg_lvl"]]
    nint = callfun[0]["nint_list"][callfun[0]["current_cvg_lvl"]]

    all_coeffs_min,all_coeffs_max = Make_Init_bounds_coeffs(nloop,ncoeff,coeff_ampl_o,k_infl,k_max,coeff_ampl_min)

    x_min = Package_all_coeffs(all_coeffs_min,callfun)
    x_max = Package_all_coeffs(all_coeffs_max,callfun)

    rand_eps = coeff_ampl_min
    rand_dim = 0
    for i in range(callfun[0]['coeff_to_param_list'][0].shape[0]):
        if ((x_max[i] - x_min[i]) > rand_eps):
            rand_dim +=1

    print('Number of initialization dimensions : ',rand_dim)

    sampler = UniformRandom(d=rand_dim)

    n_opt = 0

    while (n_opt < n_opt_max):
        
        if ((n_opt % freq_erase_dict) == 0):
            
            hash_dict = {}
            _ = SelectFiles_Action(store_folder,hash_dict)

        n_opt += 1
        
        print('Optimization attempt number : ',n_opt)

        callfun[0]["current_cvg_lvl"] = 0
        ncoeff = callfun[0]["ncoeff_list"][callfun[0]["current_cvg_lvl"]]
        nint = callfun[0]["nint_list"][callfun[0]["current_cvg_lvl"]]
        
        if (LookForTarget):
            
            all_coeffs_avg = Gen_init_avg(nTf,nbs,nbf,mass_mul,ncoeff,all_coeffs_slow_load,all_coeffs_fast_load_list=all_coeffs_fast_load_list,callfun=callfun,Rotate_fast_with_slow=Rotate_fast_with_slow,Optimize_Init=Optimize_Init,Randomize_Fast_Init=Randomize_Fast_Init,mul_loops=mul_loops)        

            x_avg = Package_all_coeffs(all_coeffs_avg,callfun)
        
        else:
            
            x_avg = np.zeros((callfun[0]['coeff_to_param_list'][callfun[0]["current_cvg_lvl"]].shape[0]),dtype=np.float64)
            
        
        x0 = np.zeros((callfun[0]['coeff_to_param_list'][callfun[0]["current_cvg_lvl"]].shape[0]),dtype=np.float64)
        
        xrand = sampler.random()
        
        rand_dim = 0
        for i in range(callfun[0]['coeff_to_param_list'][callfun[0]["current_cvg_lvl"]].shape[0]):
            if ((x_max[i] - x_min[i]) > rand_eps):
                x0[i] = x_avg[i] + x_min[i] + (x_max[i] - x_min[i])*xrand[rand_dim]
                rand_dim +=1
            else:
                x0[i] = x_avg[i]

        if save_init:
            
            print('Saving init state')

            Write_Descriptor(x0,callfun,'init.txt')

            if Save_img :
                plot_all_2D(x0,nint_plot_img,callfun,'init.png',fig_size=img_size,color=color)        

            if Save_thumb :
                plot_all_2D(x0,nint_plot_img,callfun,'init_thumb.png',fig_size=thumb_size,color=color)        
                
            # if Save_anim :
                # plot_all_2D_anim(x0,nint_plot_anim,callfun,'init.mp4',nperiod_anim,Plot_trace=Plot_trace_anim,fig_size=vid_size,dnint=dnint)
            
            if Save_Newton_Error :
                plot_Newton_Error(x0,callfun,'init_newton.png')

            # print(1/0)
            
        f0 = Compute_action_onlygrad(x0,callfun)
        best_sol = current_best(x0,f0)

        GoOn = (best_sol.f_norm < max_norm_on_entry)
        
        i_optim_param = 0
        
        while GoOn:
            # Set correct optim params
            
            inner_tol = 0.
            
            rdiff = None
            gradtol = gradtol_list[i_optim_param]
            inner_maxiter = inner_maxiter_list[i_optim_param]
            maxiter = maxiter_list[i_optim_param]
            outer_k = outer_k_list[i_optim_param]
            store_outer_Av = store_outer_Av_list[i_optim_param]
            
            print('Action Grad Norm on entry : ',best_sol.f_norm)
            print('Optim level : ',i_optim_param+1,' / ',n_optim_param , '    Resize level : ',callfun[0]["current_cvg_lvl"]+1,' / ',n_reconverge_it_max+1)
            
            F = lambda x : Compute_action_onlygrad(x,callfun)
            
            inner_M = None

            if (krylov_method == 'lgmres'):
                jac_options = {'method':krylov_method,'rdiff':rdiff,'outer_k':outer_k,'inner_inner_m':inner_maxiter,'inner_store_outer_Av':store_outer_Av,'inner_tol':inner_tol,'inner_M':inner_M }
            elif (krylov_method == 'gmres'):
                jac_options = {'method':krylov_method,'rdiff':rdiff,'outer_k':outer_k,'inner_tol':inner_tol,'inner_M':inner_M }
            else:
                jac_options = {'method':krylov_method,'rdiff':rdiff,'outer_k':outer_k,'inner_tol':inner_tol,'inner_M':inner_M }

            if (Use_exact_Jacobian):

                FGrad = lambda x,dx : Compute_action_hess_mul(x,dx,callfun)
                jacobian = ExactKrylovJacobian(exactgrad=FGrad,**jac_options)

            else: 
                jacobian = scipy.optimize.nonlin.KrylovJacobian(**jac_options)

            try : 
                
                x0 = np.copy(best_sol.x)
                opt_result = scipy.optimize.nonlin.nonlin_solve(F=F,x0=x0,jacobian=jacobian,verbose=disp_scipy_opt,maxiter=maxiter,f_tol=gradtol,line_search=line_search,callback=best_sol.update,raise_exception=False)
                
            except Exception as exc:
                
                print(exc)
                print("Value Error occured, skipping.")
                GoOn = False
                raise(exc)
                
            SaveSol = False
            
            if (GoOn and Check_Escape):
                
                Escaped,_ = Detect_Escape(best_sol.x,callfun)

                if Escaped:
                    print('One loop escaped. Starting over')    
                    
                GoOn = GoOn and not(Escaped)
                
            if (GoOn and Look_for_duplicates):

                Action,GradAction = Compute_action(best_sol.x,callfun)
                
                Found_duplicate,file_path = Check_Duplicates(best_sol.x,callfun,hash_dict,store_folder,duplicate_eps)
                
                if (Found_duplicate):
                
                    print('Found Duplicate !')   
                    print('Path : ',file_path)
                    
                GoOn = GoOn and not(Found_duplicate)
                
            if (GoOn):
                
                ParamFoundSol = (best_sol.f_norm < foundsol_tol)
                ParamPreciseEnough = (best_sol.f_norm < gradtol_max)
                print('Opt Action Grad Norm : ',best_sol.f_norm)
            
                Newt_err = Compute_Newton_err(best_sol.x,callfun)
                Newt_err_norm = np.linalg.norm(Newt_err)/(nint*nbody)
                NewtonPreciseGood = (Newt_err_norm < Newt_err_norm_max)
                NewtonPreciseEnough = (Newt_err_norm < Newt_err_norm_max_save)
                print('Newton Error : ',Newt_err_norm)
                
                CanChangeOptimParams = i_optim_param < (n_optim_param-1)
                
                CanRefine = (callfun[0]["current_cvg_lvl"] < n_reconverge_it_max)
                
                if CanRefine :
                    
                    all_coeffs_coarse = Unpackage_all_coeffs(best_sol.x,callfun)
                    ncoeff_coarse = callfun[0]["ncoeff_list"][callfun[0]["current_cvg_lvl"]]
                    
                    callfun[0]["current_cvg_lvl"] += 1
                    ncoeff_fine = callfun[0]["ncoeff_list"][callfun[0]["current_cvg_lvl"]]

                    all_coeffs_fine = np.zeros((nloop,ndim,ncoeff_fine,2),dtype=np.float64)
                    # all_coeffs_fine[:,:,0:ncoeff_coarse,:] = np.copy(all_coeffs_coarse)
                    for k in range(ncoeff_coarse):
                        all_coeffs_fine[:,:,k,:] = all_coeffs_coarse[:,:,k,:]
                        
                    x_fine = Package_all_coeffs(all_coeffs_fine,callfun)
                    f_fine = Compute_action_onlygrad(x_fine,callfun)
                    f_fine_norm = np.linalg.norm(f_fine)
                    
                    NeedsRefinement = (f_fine_norm > 3*best_sol.f_norm)
                    
                    callfun[0]["current_cvg_lvl"] += -1
                
                else:
                    
                    NeedsRefinement = False

                NeedsChangeOptimParams = GoOn and CanChangeOptimParams and not(ParamPreciseEnough) and not(NewtonPreciseGood) and not(NeedsRefinement)
                
                # print("ParamFoundSol ",ParamFoundSol)
                # print("ParamPreciseEnough ",ParamPreciseEnough)
                # print("NewtonPreciseEnough ",NewtonPreciseEnough)
                # print("NewtonPreciseGood ",NewtonPreciseGood)
                # print("NeedsChangeOptimParams ",NeedsChangeOptimParams)
                # print("CanChangeOptimParams ",CanChangeOptimParams)
                # print("NeedsRefinement ",NeedsRefinement)
                # print("CanRefine ",CanRefine)
                
                if GoOn and not(ParamFoundSol):
                
                    GoOn = False
                    print('Optimizer could not zero in on a solution')

                if GoOn and not(ParamPreciseEnough) and not(NewtonPreciseEnough) and (not(CanChangeOptimParams) or not(CanRefine)):
                
                    GoOn = False
                    print('Newton Error too high, discarding solution')
                
                if GoOn and ParamPreciseEnough and not(NewtonPreciseEnough) and not(NeedsRefinement):

                    GoOn=False
                    print("Stopping Search : there might be something wrong with the constraints")
                    # SaveSol = True
                
                if GoOn and NewtonPreciseGood :

                    GoOn = False
                    print("Stopping Search : Found solution")
                    SaveSol = True
                    
                if GoOn and NewtonPreciseEnough and not(CanChangeOptimParams) :

                    GoOn = False
                    print("Stopping Search : Found approximate solution")
                    SaveSol = True

                if GoOn and  not(NeedsRefinement) and not(NeedsChangeOptimParams):
                
                    GoOn = False
                    print('Could not converge within prescibed optimizer and refinement parameters')

                if SaveSol :
                    
                    GoOn  = False
                    
                    max_num_file = 0
                    
                    for filename in os.listdir(store_folder):
                        file_path = os.path.join(store_folder, filename)
                        file_root, file_ext = os.path.splitext(os.path.basename(file_path))
                        
                        if (file_basename in file_root) and (file_ext == '.txt' ):

                            file_root = file_root.replace(file_basename,"")

                            try:
                                max_num_file = max(max_num_file,int(file_root))
                            except:
                                pass
                        
                    max_num_file = max_num_file + 1
                    
                    filename_output = store_folder+'/'+file_basename+str(max_num_file).zfill(5)

                    print('Saving solution as '+filename_output+'.*')
             
                    Write_Descriptor(best_sol.x,callfun,filename_output+'.txt')
                    
                    if Save_img :
                        plot_all_2D(best_sol.x,nint_plot_img,callfun,filename_output+'.png',fig_size=img_size,color=color)
                    
                    if Save_thumb :
                        plot_all_2D(best_sol.x,nint_plot_img,callfun,filename_output+'_thumb.png',fig_size=thumb_size,color=color)
                        
                    if Save_anim :
                        plot_all_2D_anim(best_sol.x,nint_plot_anim,callfun,filename_output+'.mp4',nperiod_anim,Plot_trace=Plot_trace_anim,fig_size=vid_size,dnint=dnint)

                    if Save_Newton_Error :
                        plot_Newton_Error(best_sol.x,callfun,filename_output+'_newton.png')
                    
                    all_coeffs = Unpackage_all_coeffs(best_sol.x,callfun)
                    np.save(filename_output+'.npy',all_coeffs)

                
                if GoOn and NeedsRefinement:
                    
                    print('Resizing')
                    
                    best_sol = current_best(x_fine,f_fine)
                    callfun[0]["current_cvg_lvl"] += 1
                    
                    ncoeff = callfun[0]["ncoeff_list"][callfun[0]["current_cvg_lvl"]]
                    nint = callfun[0]["nint_list"][callfun[0]["current_cvg_lvl"]]
                    
                if GoOn and NeedsChangeOptimParams:
                    
                    print('Changing Optimizer Parameters')
                    
                    i_optim_param += 1
                    
                
                print('')
                
        print('')
        print('')


    print('Done !')


# if __name__ == "__main__":

    # parser = argparse.ArgumentParser(description='Welcome to the targeted choreography finder')
    # parser.add_argument('-pp','--preprint_msg',nargs=1,type=None,required=False,default=None,help='Adds a systematic message before every print')
    
    # args = parser.parse_args(sys.argv[1:])
    
    # if args.preprint_msg is None:
        
        # preprint_msg = ''

    # else:    
        
        # preprint_msg = args.preprint_msg[0].strip() + ' : '

    # tstart = time.perf_counter()
    # main(preprint_msg = preprint_msg)
    # tstop = time.perf_counter()
    
    # print(preprint_msg+'Total time in seconds : ',tstop-tstart)
