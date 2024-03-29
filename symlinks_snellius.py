import os
import sys 
import argparse
from pathlib import Path
__version__ = "2023_July.v.5.0"
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("--version", "-v", action="version", version=f"Version: {__version__}")
parser.add_argument('--dir', default=None, type=str, help="FULL PATH of the directory from where you want to start symlinks check recursively\n", required=True)
parser.add_argument('--out', default=None, type=str, help="Mandatory outname\n", required=True)
parser.add_argument('--replace', default=None, help="If you want to solve by replacement.\nThis takes comma seprated argument with directoy pattern that needs to be replaced (e.g. /dir1/dir2) and replacement( e.g. /dir3/dir4).\nIn the example /dir1/dir2 will be replaced by /dir3/dir4 and then target will be checked if exist or not.\nCan be used with --update-links to solve if targets  for which new link (after replacement) exists.")
parser.add_argument('--update-links', action='store_true', help="If you want to update the symlinks on snellius (it will only update if the target data present)")

cwd = os.getcwd()

class Logger(object):
    def __init__(self, fh):
        self.log_fh = open(fh, 'a')

    def log(self, line, summary=None):
        self.log_fh.write(f"{line}\n")

def update_symlink(current_symlink, new_location):
    os.remove(current_symlink)
    os.symlink(new_location, current_symlink)

def find_and_replace(old_target, old_dir_pat, new_dir_pat):
    if old_dir_pat in old_target:
        new_target = old_target.replace(old_dir_pat, new_dir_pat)
    else:
        new_target = old_target
    return new_target

def find_symlinks_ge(directory, out, update_links, replace):
    if os.path.exists(f'symlinks.{out}.summary.logs'):
        print(f"symlinks.{out}.summary.logs file already Exists!\nPlease change --out and re-run the script.")
        sys.exit()
    else:
        logger_object = Logger(f'symlinks.{out}.summary.logs')
        header="##Warnigs\tLocation\tTarget_location\tNewTarget_location(if_found)"
        logger_object.log(header)
    counters = {"W0": 0, "W1": 0, "W2": 0, "W3": 0, "W4": 0, "W5": 0, "W6": 0,"U1": 0, "U5": 0}
    for root, dirs, files in os.walk(directory): ## recursive
        for name in files + dirs:
            path = os.path.join(root, name)
            if os.path.islink(path):
                target = os.readlink(path)
                components = target.split('/')
                components = [comp for comp in components if comp]
                full_link= False if any(('.' == item) | ('..' == item) for item in components) else True
                
                if len(components)<2:
                    line = f"Warning00:link_other_unexpected:\t{path}\t{target}\t{target}"
                    logger_object = Logger(f'symlinks.{out}.summary.logs')
                    logger_object.log(line)
                    counters["W0"] += 1
                    continue
                if (os.path.isabs(target)) & (full_link):   ## symlinks with full pat
                    symlink_path = path; target_path = target
                    old_dir_pat=""; new_dir_pat=""
                    if len(replace.split(","))==2:
                        old_dir_pat, new_dir_pat=replace.split(",")
                    else:
                        print("Please check the argument in --replace. It should be comma seperated and 2 paths")
                        exit()
                
                    new_target_path=find_and_replace(target_path, old_dir_pat, new_dir_pat) 
                    if target_path==new_target_path:
                        if os.path.exists(target_path):
                            line = f"Warning02:link_exist_without_rep\t{symlink_path}\t{target_path}\t{new_target_path}"
                            counters["W2"] += 1
                        else:
                            line = f"Warning03:link_nonexist_after_rep\t{symlink_path}\t{target_path}\t{new_target_path}"
                            counters["W3"] += 1
                    elif os.path.exists(new_target_path):
                        line = f"Warning01:link_exist_after_rep\t{symlink_path}\t{target_path}\t{new_target_path}"
                        counters["W1"] += 1
                        if update_links:
                            update_symlink(symlink_path, new_target_path)
                            line = f"Updated01:rsynclink_pgcdac_solvable\t{symlink_path}\t{target_path}\t{new_target_path}"
                            counters["U1"] += 1
                    else:
                        if os.path.exists(target_path):
                            line = f"Warning02:link_exist_without_rep\t{symlink_path}\t{target_path}\t{new_target_path}"
                            counters["W2"] += 1
                        else:
                            line = f"Warning03:link_nonexist_after_rep\t{symlink_path}\t{target_path}\t{new_target_path}"
                            counters["W3"] += 1

                else:## symlinks with relative path
                    if   (components[0]=="rsyncd-munged") & (components[1]==".."):
                        target_path='/'.join(components[1:])
                    elif (components[0]=="rsyncd-munged") & (components[1]=="."):
                        target_path='../../'+'/'.join(components[2:])
                    else:
                        target_path='/'.join(components[0:])
                    
                    os.chdir(root) 
                    if os.path.exists(target):
                        line = f"Warning04:rellink_other_existing\t{root}\t{target}\t{target_path}"
                        counters["W4"] += 1
                    elif os.path.exists(target_path):
                        if update_links:
                            update_symlink(path, target_path)
                            line = f"Updated05:rellink_rysncd_solvable\t{root}\t{target}\t{target_path}"
                            counters["U5"] += 1
                        else:
                            line = f"Warning05:rellink_rysncd_solvable\t\t{root}\t{target}\t{target_path}"
                            counters["W5"] += 1
                    else:
                        line = f"Warning06:rellink_other_nonexisting\t{root}\t{target}\t{target_path}"
                        counters["W6"] += 1
                    os.chdir(cwd)

                logger_object = Logger(f'symlinks.{out}.summary.logs')
                logger_object.log(line)
        
    if update_links:
        summs=f"##Warning00(link_other_unexpected):{counters['W0']}\n##Updated01(link_exist_after_rep):{counters['U1']}\n##Warning02(link_exist_without_rep):{counters['W2']} \
              \n##Warning03(link_notexist_after_rep):{counters['W3']}\n##Warning04(rellink_other_existing):{counters['W4']}\n##Updated5(rellink_rysncd_solvable):{counters['U5']}\
              \n##Warning06(rellink_other_nonexisting):{counters['W6']}"
    else:
        summs=f"##Warning00(link_other_unexpected):{counters['W0']}\n##Warning01(link_exist_after_rep):{counters['W1']}\n##Warning02(link_exist_without_rep):{counters['W2']} \
              \n##Warning03(link_notexist_after_rep):{counters['W3']}\n##Warning04(rellink_other_existing):{counters['W4']}\n##Warning05(rellink_rysncd_solvable):{counters['W5']} \
              \n##Warning06(rellink_other_nonexisting):{counters['W6']}"
    logger_object = Logger(f'symlinks.{out}.summary.logs')
    logger_object.log(summs)

def find_symlinks_pd(directory, out, update_links):
    if os.path.exists(f'symlinks.{out}.summary.logs'):
        print(f"symlinks.{out}.summary.logs file already Exists!\nPlease change --out and re-run the script.")
        sys.exit()
    else:
        logger_object = Logger(f'symlinks.{out}.summary.logs')
        header="##Warnigs\tLocation\tTarget_location\tNewTarget_location(if_found)"
        logger_object.log(header)
    ##
    counters = {"W0": 0, "W1": 0, "W2": 0, "W3": 0, "W4": 0, "W5": 0, "W6": 0, "W7": 0, "W8": 0, "W9": 0, "W10": 0, "U1": 0, "U4": 0, "U9": 0}

    for root, dirs, files in os.walk(directory): ## recursive
        for name in files + dirs:
            path = os.path.join(root, name)
            if os.path.islink(path):   ## check if it is symlink
                target = os.readlink(path)
                components = target.split('/')
                components = [comp for comp in components if comp]
                full_link= False if any(('.' == item) | ('..' == item) for item in components) else True
            
                if (os.path.isabs(target)) & (full_link):   ## symlinks with full path
                    symlink_path = path
                    target_path = target  
                    if len(components)<4:
                        line = f"Warning0:link_other_unexpected:\t{path}\t{target}\t{target}"
                        logger_object = Logger(f'symlinks.{out}.summary.logs')
                        logger_object.log(line)
                        counters["W0"] += 1
                        continue
                    if f"{components[0]}/{components[1]}/{components[2]}/{components[3]}" == "rsyncd-munged/home/pgcdac/DWFV2CJb8Piv_0116_pgc_data":
                        suffix_path = "/".join(components[4:])
                        new_target_path = f"/gpfs/work5/0/pgcdac/DWFV2CJb8Piv_0116_pgc_data/{suffix_path}"

                        if os.path.exists(new_target_path):
                            if update_links:
                                update_symlink(symlink_path, new_target_path)
                                line = f"Updated1:rsynclink_pgcdac_solvable\t{symlink_path}\t{target_path}\t{new_target_path}"
                                counters["U1"] += 1
                            else:
                                line = f"Warning1:rsynclink_pgcdac_solvable:\t{symlink_path}\t{target_path}\t{new_target_path}"
                                counters["W1"] += 1
                        else:
                            line = f"Warning2:rsynclink_pgcdac_unsolvable\t{symlink_path}\t{target_path}\t{new_target_path}"
                            counters["W2"] += 1

                    elif (components[0] == "rsyncd-munged") & (f"{components[1]}/{components[2]}/{components[3]}" !="home/pgcdac/DWFV2CJb8Piv_0116_pgc_data"):
                        line = f"Warning3:rsynclink_other_unsolvable\t{symlink_path}\t{target_path}\t{target_path}"
                        counters["W3"] += 1
                
                    elif f"{components[0]}/{components[1]}/{components[2]}" == "home/pgcdac/DWFV2CJb8Piv_0116_pgc_data":
                        suffix_path = "/".join(components[3:])
                        new_target_path = f"/gpfs/work5/0/pgcdac/DWFV2CJb8Piv_0116_pgc_data/{suffix_path}"
                        if os.path.exists(new_target_path):
                            if update_links:
                                update_symlink(symlink_path, new_target_path)
                                line = f"Updated4:link_pgcdac_solvable\t{symlink_path}\t{target_path}\t{new_target_path}"
                                counters["U4"] += 1
                            else:
                                line = f"Warning4:link_pgcdac_solvable\t{symlink_path}\t{target_path}\t{new_target_path}"
                                counters["W4"] += 1
                        else:
                            line = f"Warning5:link_pgcdac_unsolvable\t{symlink_path}\t{target_path}\t{new_target_path}"
                            counters["W5"] += 1
                    else:
                        if os.path.exists(target_path):
                            line = f"Warning6:link_other_existing\t{symlink_path}\t{target_path}\t{target_path}"
                            counters["W6"] += 1
                        else:
                            line = f"Warning7:link_other_nonexisting\t{symlink_path}\t{target_path}\t{target_path}"
                            counters["W7"] += 1
                
                else:## symlinks with relative path
                    if len(components)<2:
                        line = f"Warning0:symlink_other_unexpected:\t{path}\t{target}\t{target}"
                        logger_object = Logger(f'symlinks.{out}.summary.logs')
                        logger_object.log(line)
                        counters["W0"] += 1
                        continue
                    if   (components[0]=="rsyncd-munged") & (components[1]==".."):
                        target_path='/'.join(components[1:])
                    elif (components[0]=="rsyncd-munged") & (components[1]=="."):
                        target_path='../../'+'/'.join(components[2:])
                    else:
                        target_path='/'.join(components[0:])
            
                    os.chdir(root)
                    if os.path.exists(target):
                        line = f"Warning8:rellink_other_existing\t{root}\t{target}\t{target_path}"
                        counters["W8"] += 1
                    elif os.path.exists(target_path):
                        if update_links:
                            update_symlink(path, target_path)
                            line = f"Updated9:rellink_rysncd_solvable\t{root}\t{target}\t{target_path}"
                            counters["U9"] += 1
                        else:
                            line = f"Warning9:rellink_rysncd_solvable\t{root}\t{target}\t{target_path}"
                            counters["W9"] += 1
                    else:
                        line = f"Warning10:rellink_other_nonexisting\t{root}\t{target}\t{target_path}"
                        counters["W10"] += 1
                    os.chdir(cwd)
                logger_object = Logger(f'symlinks.{out}.summary.logs')
                logger_object.log(line)

    if update_links:
        summs=f"##Warning0(link_other_unexpected):{counters['W0']}\n##Updated1(rsynclink_pgcdac_solvable):{counters['U1']}\n##Warning2(rsynclink_pgcdac_unsolvable):{counters['W2']} \
              \n##Warning3(rsynclink_other_unsolvable):{counters['W3']}\n##Updated4(link_pgcdac_solvable):{counters['U4']}\n##Warning5(link_pgcdac_unsolvable):{counters['W5']} \
              \n##Warning6(link_other_existing):{counters['W6']}\n##Warning7(link_other_nonexisting):{counters['W7']}\n##Warning8(rellink_other_existing):{counters['W8']} \
              \n##Updated9(rellink_rysncd_solvable):{counters['U9']}\n##Warning10(rellink_other_nonexisting):{counters['W10']}"
    else:
        summs=f"##Warning0(link_other_unexpected):{counters['W0']}\n##Warning1(rsynclink_pgcdac_solvable):{counters['W1']}\n##Warning2(rsynclink_pgcdac_unsolvable):{counters['W2']} \
              \n##Warning3(rsynclink_other_unsolvable):{counters['W3']}\n##Warning4(link_pgcdac_solvable):{counters['W4']}\n##Warning5(link_pgcdac_unsolvable):{counters['W5']} \
              \n##Warning6(link_other_existing):{counters['W6']}\n##Warning7(link_other_nonexisting):{counters['W7']}\n##Warning8(rellink_other_existing):{counters['W8']} \
              \n##Warning9(rellink_rynscd_solvable):{counters['W9']}\n##Warning10(rellink_other_nonexisting):{counters['W10']}"
            
    logger_object = Logger(f'symlinks.{out}.summary.logs')
    logger_object.log(summs)

if __name__ == '__main__':
    args = parser.parse_args()
    path = Path(args.dir); out=args.out; update_links = args.update_links; replace=args.replace
    if replace:
        find_symlinks_ge(path, out, update_links, replace)
    else:
        find_symlinks_pd(path, out, update_links)

