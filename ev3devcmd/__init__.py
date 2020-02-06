import errno
import socket
import paramiko
import rpyc
import sys
import os
import argparse
import ev3devlogging

# We use a mirror of sftpclone v1.2.2, because it has explicit dependency 'paramiko==2.4.1',
# but we need 'paramiko==2.6.0' for ev3devcmd!
# When we used sftpclone v1.2.2 as dependency, then the entry script would thrown an version conflict error
# because ev3devcmd needs 'paramiko==2.6.0' and sftpclone needs 'paramiko==2.4.1'.
# But sftpclone v1.2.2 works fine with the newer 'paramiko==2.6.0', so we took the HACK to include a mirror of it,
# into this ev3devcmd package until a newer version of it requiring 'paramiko==2.6.0' would be available.
# This HACK solves the dependency problem, because we then don't need the   'sftpclone=1.2.2' anymore.

import ev3devcmd.sftpclone as sftpclone
#import sftpclone.sftpclone as sftpclone


import functools
print = functools.partial(print, flush=True)

from time import sleep

def checkfile(PATH):
    if not ( os.path.isfile(PATH) and os.access(PATH, os.R_OK) ):
        print("Either file '{0}' is missing or is not readable".format(PATH),file=sys.stderr)
        sys.exit(1)

def sshconnect(args):

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # like for rpyc.classic.connect we use a 3 seconds timeout for ssh.connect
        ssh.connect(args.address, username=args.username, password=args.password,timeout=3,look_for_keys=False)
    except socket.timeout as e:
        print("\nProblem: failed connecting with EV3 over ssh to '{ip}': timeout happened.\n\n         Is the EV3 maybe not connected?\n\n         Or is the address '{ip}' maybe wrong?\n         Within the Thonny IDE you can fix the EV3 address in \"Tools > Options\" menu.\n         With the ev3dev command you can give the EV3 address as an option.".format(ip=args.address))
        sys.exit(1)
    except paramiko.ssh_exception.AuthenticationException as e:
        print("\nProblem: failed connecting with EV3 over ssh: authentication failed.\n\n          Within the Thonny IDE you can the credentials in \"Tools > Options\" menu.\n         With the ev3dev command you can give the credentials as options.")
        sys.exit(1)
    except Exception as e:
        print(e)
        sys.exit(1)

    return ssh


def file_exist_on_ev3(ftp,filepath):
    file_exist=True
    try:
        ftp.lstat(filepath)
    except FileNotFoundError:
        file_exist=False
    return  file_exist

def line_buffered(f):
    line_buf = ""
    while not f.channel.exit_status_ready():
        b=f.read(1)
        line_buf += b.decode('utf-8')
        if line_buf.endswith('\n'):
            yield line_buf
            line_buf = ''


def ev3rootdir(args):
    return '/home/'+ args.username + '/'

def upload(args):
    # allow any source path on pc ( relative paths taken relative from cwd where this command is executed)
    # allow only destination path in homedir on ev3 
    
    filename=os.path.basename(args.file)
    srcdir=os.path.normpath(os.path.join(os.getcwd(), os.path.dirname(args.file)))
    srcpath=os.path.join(srcdir,filename)
    checkfile(srcpath)

    # for simplicity:  can only upload file within homedir
    destpath=ev3rootdir(args) + filename
    if args.subdir is not None:
        destpath=os.path.join(ev3rootdir(args),args.subdir,filename)

    print("uploading file to EV3 as: " + destpath)

    ssh=sshconnect(args)
    ftp = ssh.open_sftp()

    if args.force or not file_exist_on_ev3(ftp,destpath):
        ftp.put(srcpath, destpath)
        ftp.chmod(destpath, 0o775)
        ftp.close()
        ssh.close()
        print("succesfully uploaded file to EV3 as: " + destpath)
    else:
        print("Failed to upload because file '{0}' already exists on EV3. Use --force option to force overwriting.".format(destpath),file=sys.stderr)
        ftp.close()
        ssh.close()
        sys.exit(1)

    # quickly show in modal dialog in thonny before it exits
    print("\n\nupload succesfull")


def start(args):

    # for safety:  we can only upload file into  homedir (or subdir of homedir)
    # so programs we start also only in homedir (or subdir of homedir)

    filename=os.path.basename(args.file)
    srcpath=ev3rootdir(args) + filename
    if args.subdir is not None:
        srcpath=os.path.join(ev3rootdir(args),args.subdir,filename)

    print("Start the execution of the file '{0}' on the EV3'.".format(srcpath))
    ssh=sshconnect(args)
    ftp = ssh.open_sftp()

    if not file_exist_on_ev3(ftp,srcpath):
        print("The file '{0}' doesn't exist on the EV3.".format(srcpath),file=sys.stderr)
        ftp.close()
        ssh.close()
        sys.exit(1)


    try:
        print("Running start command on the EV3.")
        client_shell = ssh.invoke_shell()
        stdin = client_shell.makefile('wb')
        stdout = client_shell.makefile('rb')

        # getting sudo rights
        source=r'''
            runprogram(){
                program=$(realpath "$1")
                errlogfile="$program".err.log
                directory=$(dirname "$program")
                /usr/bin/brickrun --directory $directory -- $program 2> $errlogfile  
                if [[ ! -s $errlogfile ]]; then rm -f $errlogfile; fi
            }
        '''

        source= source + '''
            runprogram "{}" >/dev/null &
        '''.format(srcpath)

        stdin.write(source)
        stdin.write('exit\n')
        stdin.flush()

        # read stdout output  line for line so that we can show progress
        # note: stdout also contains stderr of shell

        # stdin gets also output to stdout, so filter that first out (don't print)
        for line in line_buffered(stdout):
            if ("exit" in line):
                break

        # only display stdout without prompt($)
        for line in line_buffered(stdout):
            if (not "$" in line) and (not line.startswith('>')) and (not "Last login:" in line) and (not "logout" in line):
                  print(line, end = '')
    except Exception as inst:
        print(inst)
        print("Failed running start command on the EV3.",file=sys.stderr)
        ftp.close()
        ssh.close()
        sys.exit(1)

    print("\n\nStart succesfully")

    ftp.close()
    ssh.close()










# stop, first tries fast stop_rpyc, but if no rpyc server on EV3, then switches to slower stop_ssh over ssh
def stop(args):
    print("stop/kill all programs and motors/sound on EV3\n\n")

    try:
        stop_rpyc(args)
    except socket.timeout as e:
        if args.rpyc_only:
            print("\nProblem: failed connecting with EV3 over rpyc: timeout happened.\n         EV3 maybe not connected?\n         Within the Thonny IDE you can fix the EV3 address in \"Tools > Options\" menu.\n         With the ev3dev command you can give the EV3 address as an option.")
            sys.exit(1)
        else:
            print("rpyc connection failed, try ssh connection\nNote: you can configure a longer rpyc_timeout!")
            stop_ssh(args)



# fast stop using rpyc
def stop_rpyc(args):

    ip=args.address
    port = rpyc.classic.DEFAULT_SERVER_PORT
    # print("port",port)
    # print("address",ip)
    # print("args",args)
    stream=rpyc.SocketStream.connect(ip,port,timeout=args.rpyc_timeout,attempts=1)
    conn=rpyc.classic.connect_stream(stream)

    #NOTE: default: timeout=3 but does 6 attemps => total of 18 seconds
    ## rpyc.classic.connect has by default a timeout of 3  seconds (see rpyc.SocketStream.connect)
    #conn = rpyc.classic.connect(ip) # host name or IP address of the EV3

    os= conn.modules['os']
    sudoPassword=args.password


    print("kill programs running on EV3")
    # kill programs running on ev3
    command="kill -9 -`pgrep -f 'python3 " + ev3rootdir(args) + "'`"

    # no sudo needed, program runs as user robot
    os.system(command)

    print("stop motors on EV3")
    # kill motors
    ev3= conn.modules['ev3dev.ev3']
    for m in ev3.list_motors():
        m.reset()

    print("stop sound on EV3")
    # kill sound via beep
    command='pkill -f /usr/bin/aplay'
    os.system('echo %s|sudo -S %s' % (sudoPassword, command))
    # kill sound aplay
    command='pkill -f /usr/bin/beep'
    os.system('echo %s|sudo -S %s' % (sudoPassword, command))

    print("set leds back to default of green")
    ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.GREEN)
    ev3.Leds.set_color(ev3.Leds.LEFT, ev3.Leds.GREEN)

    print("\n\nSuccesfully runned the command 'stop' on the EV3.")

# slow stop over ssh if not rpyc server on EV3
def stop_ssh(args):

    ssh=sshconnect(args)
    password=args.password

    try:

        # first quickly kill process, then do slower cleanup afterwards
        print("kill program running on EV3\n")
        ssh.exec_command("kill -9 -`pgrep -f 'python3 " + ev3rootdir(args) + "'`")

        # create interactive shell
        client_shell = ssh.invoke_shell()
        stdin = client_shell.makefile('wb')
        stdout = client_shell.makefile('rb')

        print("stop motors running on EV3\n")
        stdin.write(r'''
            # kill motors
            python3 -c "exec(\"import ev3dev.ev3\nfor m in ev3dev.ev3.list_motors():\n  m.reset()\")"
        ''')
        stdin.flush()
        # getting sudo rights
        stdin.write('echo {}| sudo -S echo "getting sudo rights" &> /dev/null'.format(password))
        stdin.write(r'''
            printf "stop sound on EV3\n"
            # kill sound via beep
            sudo  pkill -f /usr/bin/aplay
            
            # kill sound aplay
            sudo pkill -f /usr/bin/beep
            
            printf "set leds back to default of green\n"
            python3 -c "exec(\"import ev3dev.ev3\nev3dev.ev3.Leds.set_color(ev3dev.ev3.Leds.LEFT, ev3dev.ev3.Leds.GREEN)\nev3dev.ev3.Leds.set_color(ev3dev.ev3.Leds.RIGHT, ev3dev.ev3.Leds.GREEN)\")"
        ''')
        stdin.write('exit\n')
        stdin.flush()
        # read stdout output  line for line so that we can show progress
        # note: stdout also contains stderr of shell

        # stdin gets also output to stdout, so filter that first out (don't print)
        for line in line_buffered(stdout):
            if ("exit" in line):
                break

        # only display stdout without prompt($)
        for line in line_buffered(stdout):
            if (not "$" in line) and (not line.startswith('>')) and (not password in line) and (not "Last login:" in line) and (not "logout" in line):
                print(line, end = '')
    except Exception as inst:
        print("Failed executing stop on the EV3.",file=sys.stderr)
        ssh.close()
        sys.exit(1)

    print("\n\nSuccesfully runned the command 'stop' on the EV3.")
    ssh.close()



def download(args):
    # allow only source path in homedir on ev3 
    # allow any destination path on pc ( relative paths taken relative from cwd where this command is executed)


    # for simplicity:  can only download file from  homedir on ev3, (or any subdir of homedir)
    #                  so we only need to specify destpath of file on pc
    filename=os.path.basename(args.file)
    srcpath=ev3rootdir(args) + filename
    if args.subdir is not None:
        srcpath=os.path.join(ev3rootdir(args),args.subdir,filename)
    destdir=os.path.normpath(os.path.join(os.getcwd(), os.path.dirname(args.file)))
    destpath=os.path.join(destdir,filename)

    if not os.path.isdir(destdir):
        print("Failed to download because destination directory '{0}' does not exists.".format(os.path.dirname(destpath)),file=sys.stderr)
        sys.exit(1)
    if os.path.isfile(destpath) and not args.force:
        print("Failed to download because destination '{0}' already exists. Use --force option to force overwriting.".format(destpath),file=sys.stderr)
        sys.exit(1)

    print("Download file '{0}'".format(srcpath))
    ssh=sshconnect(args)
    ftp = ssh.open_sftp()

    if not file_exist_on_ev3(ftp,srcpath):
        print("The file '{0}' doesn't exist on the EV3.".format(srcpath),file=sys.stderr)
        ftp.close()
        ssh.close()
        sys.exit(1)

    try:
        ftp.get(srcpath, destpath)
    except IOError:
        print("Failed to download the file from the EV3 at '{0}  to file '{1}'.".format(srcpath),file=sys.stderr)
        ftp.close()
        ssh.close()
        sys.exit(1)

    ftp.close()
    ssh.close()
    print("succesfully downloaded the file from the EV3 at '{0}' to file '{1}'.".format(srcpath,destpath) )


def listfiles(args):
    """ list files using tree command"""
    targetdir=ev3rootdir(args)
    if args.subdir is not None:
        targetdir=ev3rootdir(args)+args.subdir

    command= 'tree -nF ' + targetdir

    print("List files in '{0}':\n".format(targetdir))
    ssh=sshconnect(args)
    stdin, stdout, stderr = ssh.exec_command(command,get_pty=True)
    stdin.write(args.password+'\n')
    stdin.flush()
    data = stdout.read().splitlines()
    for line in data:
        line = str(line, 'utf-8')
        if not args.password in line:
            print(line)
    data = stderr.read().splitlines()
    for line in data:
        print(str(line, 'utf-8'),file=sys.stderr)
    ssh.close()


def delete(args):
    # deleting a basename => deletes file in user's home directory
    srcpath=args.file
    filename=os.path.basename(srcpath)
    destpath=ev3rootdir(args) + filename
    if args.subdir is not None:
        destpath=os.path.join(ev3rootdir(args),args.subdir,filename)

    print("Delete on EV3 the file: " + destpath)
    ssh=sshconnect(args)
    ftp = ssh.open_sftp()
    try:
        ftp.remove(destpath)
        print("succesfully deleted on EV3 the file: " + destpath)
    except Exception as ex:
        print(str(ex),file=sys.stderr)
    finally:
        ftp.close()
        ssh.close()



def rmdir(args):
    destpath=ev3rootdir(args) + args.subdir

    print("Delete on EV3 the directory: " + destpath)
    ssh=sshconnect(args)
    ftp = ssh.open_sftp()
    try:
        ftp.rmdir(destpath)
        print("succesfully deleted on EV3 the directory: " + destpath)
    except Exception as ex:
        print(str(ex),file=sys.stderr)
    finally:
        ftp.close()
        ssh.close()



def mkdir(args):
    destpath=ev3rootdir(args) + args.subdir

    print("Create on EV3 the directory: " + destpath)
    ssh=sshconnect(args)
    ftp = ssh.open_sftp()
    try:
        ftp.mkdir(destpath)
        print("succesfully created on EV3 the directory: " + destpath)
    except Exception as ex:
        print(str(ex),file=sys.stderr)
        print("ERROR - Failed creating the directory: " + destpath + ". Maybe parent directory does not yet exist.",file=sys.stderr)
    finally:
        ftp.close()
        ssh.close()






# base mirror of a sourcedir into homedir which preserves . files in homedir
#----------------------------------------------------------------------------
# note: base mirror removes all files not in sourcedir from homedir (except . files in homedir)
orig_rmdir = None
orig_remove = None
base_remote_path = None

def new_remove(remote_path):
    """ remove which skips removing files starting with '.' """
    global orig_remove
    global base_remote_path
    if remote_path.startswith( os.path.join(base_remote_path,".") ):
        return
    orig_remove(remote_path)

def new_rmdir(remote_path):
    """ remove which skips removing directories starting with '.' """
    global orig_rmdir
    global base_remote_path
    if remote_path.startswith( os.path.join(base_remote_path,".") ):
        return

    orig_rmdir(remote_path)


def rexists(sftp, path):
    """os.path.exists for paramiko's sftp object
    """
    try:
        sftp.stat(path)
    except IOError as e:
        if e.errno == errno.ENOENT:
            return False
        raise
    else:
        return True


def base_mirror(args, local_path, dest_subdir, cleanup=False, skip_all_hidden=False ):

    dest_path=ev3rootdir(args)
    if dest_subdir:
        dest_path=dest_path + dest_subdir



    # do extra connect  only for nice error message in case of failure (don't want to hack sftpclone library for that)
    ssh=sshconnect(args)

    remote_url=r'{username}:{password}@{server}:{dest_dir}'.format(username=args.username, password=args.password,server=args.address,dest_dir=dest_path)

    # disable the default of DEBUG logging into CRITICAL only logging
    import logging
    sftpclone.logger = sftpclone.configure_logging(level=logging.ERROR)
    sync = sftpclone.SFTPClone(local_path,remote_url)

    # exclude files/dirs starting with '.' in rootdir from syncing/removing
    mirroring_into_rootdir = not dest_subdir
    if mirroring_into_rootdir:
        # 1) exclude from removing the files/dirs starting with '.' in rootdir of destination dir
        # REASON: to protect hidden . files and dirs in homedir on ev3 (eg. /home/robot/.bashrc) from removal!
        # we implement this by patching sftp.remove and sftp.rmdir
        global orig_remove
        global base_remote_path
        base_remote_path=sync.remote_path
        global orig_rmdir
        orig_remove=sync.sftp.remove
        sync.sftp.remove=new_remove
        orig_rmdir=sync.sftp.rmdir
        sync.sftp.rmdir=new_rmdir

        # 2) exclude from syncing files/dirs starting with '.' in root of sourcedir
        # REASON: to protect hidden . files and dirs in homedir on ev3 from be overwritten!
        import glob
        # expand local path to real path  => important for getting paths right in exclude list which is compared with the realpath
        # note: within sftpclone paths give are also converted to real paths
        local_path = os.path.realpath(os.path.expanduser(local_path))
        sync.exclude_list = {
            g
            for g in glob.glob(sftpclone.path_join(local_path, ".*"))
        }



    # https://en.wikipedia.org/wiki/Glob_(programming)
    # The “**” pattern means “this directory and all subdirectories, recursively”.
    # The"**/*" pattern means all files/dirs in “this directory and all subdirectories, recursively”.
    #       `-> all files/dirs recursively within this directory
    # The"**/__pycache__" pattern means all files/dirs recursively within this directory with the exact name "__pycache__"

    # exclude directories named __pycache__
    # note: if a directory is in the sync.exclude_list then anything below it is also excluded!
    # REASON: efficiency!!
    from pathlib import Path
    for item in Path(local_path).glob('**/__pycache__'):
        sync.exclude_list.add(os.path.realpath(item))

    # if we are mirroring then  we can skip all hidden files from mirror when skip_all_hidden==True
    if (not cleanup) and skip_all_hidden:
       for item in Path(local_path).glob( '**/.*'):
           sync.exclude_list.add(os.path.realpath(item))

    # create destination subdirectory before mirroring if it not yet exists
    # note: we skip this when doing a cleanup
    if (not cleanup) and dest_subdir and (not rexists(sync.sftp, dest_path)):
        try:
            sync.sftp.mkdir(dest_path)
        except Exception as ex:
            print(str(ex),file=sys.stderr)
            print("ERROR - Failed creating the directory: " + dest_path + ". Maybe parent directory does not yet exist.",file=sys.stderr)
            sys.exit(1)

    sync.run()

    # if cleanup a directory(mirroring with an empty dir) and destination is a subdirectory
    # then we remove the empty directory afterwards
    if cleanup and dest_subdir:
       try:
           sync.sftp.rmdir(dest_path)
       except Exception as ex:
           print(str(ex),file=sys.stderr)
           print("ERROR - Failed removing the directory: " + dest_path + ". Maybe directory does not exist.",file=sys.stderr)
           sys.exit(1)

#  mirror and cleanup ; implemented using base_mirror
#----------------------------------------------------


def check_subdir(subdir):
    if subdir is not None:
        if(  os.path.isabs(subdir) ):
            print("Subdir argument '{0}' is not a relative path".format(subdir),file=sys.stderr)
            sys.exit(1)

def mirror(args):

    dest_subdir= args.subdir
    check_subdir(dest_subdir)

    src_path=args.sourcedir
    skip_all_hidden= not args.all

    print("Mirror")
    base_mirror(args, src_path, dest_subdir,skip_all_hidden=skip_all_hidden)
    print("\n\nmirror succesfull")

def cleanup(args):
    # cleanup of homedir[/SUBDIR]; other locations are not cleanable (because to dangerous);

    dest_subdir= args.subdir
    check_subdir(dest_subdir)

    import tempfile
    src_path=tempfile.mkdtemp()

    print("Cleanup")
    base_mirror(args, src_path, dest_subdir, cleanup=True)
    print("\n\ncleanup succesfull")


def install_rpyc_server(args):

    print("install rpyc_server")
    ssh=sshconnect(args)
    ftp = ssh.open_sftp()

    dir_path = os.path.dirname(os.path.realpath(__file__))

    print("install rpyc-4.1.2 package on EV3 (can take 60 seconds)")

    ftp.put(os.path.join(dir_path,'res','rpyc-4.1.2.tar.gz'), '/tmp/rpyc-4.1.2.tar.gz')

    stdin, stdout, stderr = ssh.exec_command('sudo tar -C /tmp -xzvf /tmp/rpyc-4.1.2.tar.gz',get_pty=True)
    stdin.write(args.password+'\n')
    stdin.flush()
    data = stdout.read().splitlines()
    data = stderr.read().splitlines()

    stdin, stdout, stderr = ssh.exec_command('cd /tmp/rpyc-4.1.2/;sudo python3 setup.py install',get_pty=True)
    stdin.write(args.password+'\n')
    stdin.flush()
    data = stdout.read().splitlines()
    data = stderr.read().splitlines()

    print("add rpycd.service")

    ftp.put(os.path.join(dir_path,'res','rpycd.service'), '/tmp/rpycd.service')


    stdin, stdout, stderr = ssh.exec_command('sudo mv /tmp/rpycd.service /etc/systemd/system/rpycd.service',get_pty=True)
    stdin.write(args.password+'\n')
    stdin.flush()
    data = stdout.read().splitlines()
    data = stderr.read().splitlines()

    print("enable  rpycd.service")

    stdin, stdout, stderr = ssh.exec_command('sudo systemctl enable rpycd.service',get_pty=True)
    stdin.write(args.password+'\n')
    stdin.flush()
    data = stdout.read().splitlines()
    # for line in data:
    #     print(line)
    data = stderr.read().splitlines()
    # for line in data:
    #     print(line,file=sys.stderr)

    print("start rpycd.service (can take 30 seconds)")

    # restart instead of start, to make sure older version is stopped first
    stdin, stdout, stderr = ssh.exec_command('sudo systemctl restart rpycd.service',get_pty=True)
    stdin.write(args.password+'\n')
    stdin.flush()
    data = stdout.read().splitlines()
    data = stderr.read().splitlines()

    # add extra sleep to be sure rpyc server is started when we say finished!
    #  => because otherwise window says finished but rpyc server not yet started
    sleep(30)

    print("\n\nfinished")


    ftp.close()
    ssh.close()

def install_ev3devlogging(args):
    print("install ev3devlogging package on EV3")
    ssh=sshconnect(args)
    ftp = ssh.open_sftp()

    ftp.put(ev3devlogging.__file__, '/tmp/ev3devlogging.py')

    stdin, stdout, stderr = ssh.exec_command('sudo mv /tmp/ev3devlogging.py /usr/lib/python3/dist-packages/ev3devlogging.py',get_pty=True)
    stdin.write(args.password+'\n')
    stdin.flush()
    data = stdout.read().splitlines()
    data = stderr.read().splitlines()

    print("\n\nfinished")

    ftp.close()
    ssh.close()



class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
      pass

def main(argv=None):
    """
    Entry point for the command line tool 'ev3dev'.
    """


    if argv is None:
        argv = sys.argv

    # get default values from environment or from hardcoded defaults
    # note: with commandline options you can overwrite the default values
    default_ip=os.environ.get('EV3IP') or '192.168.0.1'
    default_user=os.environ.get('EV3USERNAME') or 'robot'
    default_password=os.environ.get('EV3PASSWORD') or 'maker'


    if "-V" in  argv[1:] or "--version" in argv[1:]:
        from ev3devcmd import version as cmdversion
        print("version: " + cmdversion.__version__)
        sys.exit(0)

    # use RawDescriptionHelpFormatter: which allows formatting you desription with newlines yourself, however the commandline options
    #                                  are formatted automatically (newlines you place are ignored).
    # use ArgumentDefaultsHelpFormatter: so that also default values are shown in help message
    # note: both are combined in CustomFormatter class above
    parser = argparse.ArgumentParser(prog='ev3dev', formatter_class=CustomFormatter,
                                     description="Commands to upload/start/download/delete/cleanup programs on the EV3.\nAll file operations on the EV3 are only allowed within the user's homedir.\nComplete documentation at: https://github.com/ev3dev-python-tools/ev3devcmd/.")

    parser.add_argument("-V", "--version",
                        action='store_true',
                        help="Show version info",default=argparse.SUPPRESS)

    parser.add_argument('-a', '--address',action='store',default=default_ip,help="network address of EV3. Can also be set with EV3IP environment variable.")
    parser.add_argument('-u', '--username',action='store',default=default_user,help="username used to login with ssh on EV3. Can also be set with EV3USERNAME environment variable.")
    parser.add_argument('-p', '--password',action='store',default=default_password,help="password used to login with ssh on EV3. Can also be set with EV3PASSWORD environment variable.")

    parser.add_argument('--sleep-after',type=int,default=0,help="Time to sleep after executing command. Mainly needed for gui to let user read output of command before closing it.")


    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True

    # create the parser for the "list" command
    parser_list_description ="list all files in homedir on EV3"
    parser_list = subparsers.add_parser('list', description=parser_list_description, help=parser_list_description,formatter_class=CustomFormatter)
    parser_list.set_defaults(func=listfiles)
    parser_list.add_argument('subdir', nargs='?', type=str,help="subdirectory in homedir on EV3; Must be relative path.")



    # create the parser for the "upload" command
    parser_upload_description ="upload file to homedir on EV3"
    parser_upload = subparsers.add_parser('upload', description=parser_upload_description, help=parser_upload_description,formatter_class=CustomFormatter)
    parser_upload.add_argument('file', type=str,help="source path on pc; destination path on EV3 is /home/USERNAME/[subdir/]basename(file)")
    parser_upload.add_argument('subdir', nargs='?', type=str,help="subdirectory in homedir on EV3; Must be relative path.")
    parser_upload.add_argument('-f', '--force',action='store_true',help="overwrite file if already exist")
    parser_upload.set_defaults(func=upload)


    # create the parser for the "download" command
    parser_download_description = 'download file from EV3'
    parser_download = subparsers.add_parser('download',description=parser_download_description,help=parser_download_description,formatter_class=CustomFormatter)
    parser_download.add_argument('file', type=str,help="destination path on pc; source path on EV3 is /home/USERNAME/[subdir/]basename(file)")
    parser_download.add_argument('subdir', nargs='?', type=str,help="subdirectory in homedir on EV3; Must be relative path.")
    parser_download.add_argument('-f', '--force',action='store_true',help="overwrite file if already exist")
    parser_download.set_defaults(func=download)
    # create the parser for the "delete" command
    parser_delete_description='delete a file on EV3'
    parser_delete = subparsers.add_parser('delete', description=parser_delete_description,help=parser_delete_description,formatter_class=CustomFormatter)
    parser_delete.add_argument('file', type=str,help="filename of file in EV3's homedir[/subdir]; directory of file argument is ignored;  delete /home/USERNAME/[subdir/]basename(file)")
    parser_delete.add_argument('subdir', nargs='?', type=str,help="subdirectory in homedir on EV3; Must be relative path.")
    parser_delete.set_defaults(func=delete)
    # create the parser for the "clean" command
    parser_clean_description='delete all files in homedir[/subdir] on EV3'
    parser_clean = subparsers.add_parser('cleanup',description=parser_clean_description, help=parser_clean_description,formatter_class=CustomFormatter)
    parser_clean.add_argument('subdir', nargs='?', type=str,help="subdirectory in homedir on EV3; if specified only that directory gets cleaned instead of the whole homedir. Must be relative path.\nHidden files/dirs starting with '.' in homedir on EV3 are preserved by excluding them from cleanup.")
    parser_clean.set_defaults(func=cleanup)
    # create the parser for the "mirror" command
    # note: help message is shown for general help "ev3dev -h", long description for specific help "ev3dev mirror -h"
    parser_mirror_help= "Mirror sourcedir into homedir[/subdir] on EV3. Subdirs within sourcedir are recursively mirrored."
    parser_mirror_description= \
    "Mirror sourcedir into homedir[/subdir] on EV3.\nSubdirs within sourcedir are recursively mirrored.\n"\
    + "Files/dirs within homedir[/subdir] but not in sourcedir are removed.\n"\
    + "Hidden files/dirs starting with '.' in homedir on EV3 are ALWAYS PRESERVED by excluding mirroring\n"\
    + "of hidden files at the root of the sourcedir into the homedir.\n"\
    + "Directories with the name '__pycache__' are ALWAYS excluded from mirroring.\n"\
    + "\n"\
    + "When uploading a script then the executable is set and a shebang added if not yet there.\n" \
    + "If using mirror on linux/macos then make sure the main script is executable and has a shebang line,\n" \
    + "or otherwise upload the main script separately afterwards.\n" \
    + "If using mirror on windows then upload the main script separately afterwards. Note that on windows\n" \
    + "you cannot set an executable bit on a file.\n"
    parser_mirror = subparsers.add_parser('mirror',description=parser_mirror_description, help=parser_mirror_help,formatter_class=CustomFormatter)
    parser_mirror.add_argument('-a', '--all',action='store_true',help="do not exclude hidden files/dirs starting with '.' from mirroring. Hidden files/dirs can only be mirrored within subdirectories. In the root of the home directory of the EV3 they are ALWAYS excluded from mirroring to protect the user's configuration files in his home directory.")
    parser_mirror.add_argument('sourcedir', type=str,help="source directory which gets mirrored.")
    parser_mirror.add_argument('subdir', nargs='?', type=str,help="subdirectory in homedir on EV3 where it gets mirrored instead of the homedir. Must be relative path.")


    parser_mirror.set_defaults(func=mirror)

    # create the parser for the "rmdir" command
    parser_rmdir_description='delete empty subdirectory in homedir on EV3; To delete a none-empty directory use "cleanup" command instead.'
    parser_rmdir = subparsers.add_parser('rmdir',description=parser_rmdir_description, help=parser_rmdir_description,formatter_class=CustomFormatter)
    parser_rmdir.add_argument('subdir', type=str,help="subdirectory in homedir on EV3 ; Must be relative path.")
    parser_rmdir.set_defaults(func=rmdir)

    # create the parser for the "mkdir" command
    parser_mkdir_description='make subdirectory in homedir on EV3'
    parser_mkdir = subparsers.add_parser('mkdir',description=parser_mkdir_description, help=parser_mkdir_description,formatter_class=CustomFormatter)
    parser_mkdir.add_argument('subdir', type=str,help="subdirectory in homedir on EV3 ; Must be relative path.")
    parser_mkdir.set_defaults(func=mkdir)

    # create the parser for the "start" command
    parser_start_description="start program on EV3; program must already be on EV3's homedir"
    parser_start = subparsers.add_parser('start',description=parser_start_description,help=parser_start_description,formatter_class=CustomFormatter)
    parser_start.add_argument('file', type=str,help="filename of file in EV3's homedir[/subdir]; directory of file argument is ignored;  start /home/USERNAME/[subdir/]basename(file)")
    parser_start.add_argument('subdir', nargs='?', type=str,help="subdirectory in homedir on EV3; Must be relative path.")
    parser_start.set_defaults(func=start)

    # create the parser for the "stop" command
    parser_stop_description="stop program/motors/sound on EV3"
    parser_stop = subparsers.add_parser('stop',description=parser_stop_description, help=parser_stop_description,formatter_class=CustomFormatter)
    # rpyc_timeout
    parser_stop.add_argument('-t', '--rpyc-timeout',type=float,help="timeout for rpyc connection", default=0.1)
    parser_stop.add_argument('-f', '--rpyc-only',action='store_true',help="only connect with rpyc and don't use ssh fallback if rpyc connection fails")
    parser_stop.set_defaults(func=stop)


    # create the parser for the "install_ev3devlogging" command
    parser_install_ev3devlogging_description ='install ev3devlogging package on the EV3 when just having installed a newly installed ev3dev image'
    parser_install_ev3devlogging = subparsers.add_parser('install_logging', description=parser_install_ev3devlogging_description, help=parser_install_ev3devlogging_description,formatter_class=CustomFormatter)
    parser_install_ev3devlogging.set_defaults(func=install_ev3devlogging)

    # create the parser for the "install_rpyc_server" command
    parser_install_rpyc_server_description = 'install rpyc server on the EV3 when just having installed a newly installed ev3dev image'
    parser_install_rpyc_server = subparsers.add_parser('install_rpyc_server', description=parser_install_rpyc_server_description, help=parser_install_rpyc_server_description,formatter_class=CustomFormatter)
    parser_install_rpyc_server.set_defaults(func=install_rpyc_server)

    # parse args,
    args=parser.parse_args(argv[1:])

    # and call the function found by parsing, and pass it the args
    args.func(args)
    sys.stdout.flush()

    # to still read output of command if it was successfull in an automatically closing GUI dialog box (eg. in Thonny IDE)
    sleep(args.sleep_after)





