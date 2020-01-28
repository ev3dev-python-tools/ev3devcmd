# ev3devcmd 

The ev3devcmd package delivers
 
   * the **ev3devcmd library** delivering the commands {list,upload,start,download,delete,cleanup,install_additions,softreset,stop}
   * the **ev3dev command-line tool** wrapping  the ev3devcmd library for easy access on the command-line

The ev3devcmd library lets you integrate support for the EV3 into an IDE. For example with the Thonny IDE you
can install the thonny-ev3dev plugin which uses the ev3devcmd library to implement support for the EV3. The plugin adds
buttons like "upload program", or "download the log" which behind the scene use the ev3devcmd library. <br>
See: https://github.com/ev3dev-python-tools/thonny-ev3dev/wiki

The ev3dev command-line tool lets 
you use the functionality of the ev3devcmd library on the command-line without using any IDE.

The ev3devcmd package plugin assumes by default that you use USB tethering mode on the ev3 with the default ev3dev 
credentials to connect with usb cable to the ev3:

    ip=192.168.0.1
    user=robot
    password=maker

The reason for using usb tethering is the fixed ip=192.168.0.1. Once setup you can allows access the EV3 brick by 
just connect the usb cable and you can just connect using this ip address. 
For more details about usb tethering mode see: https://github.com/ev3dev-python-tools/thonny-ev3dev/wiki/Connect-with-EV3


However you can also use a different ip,user and password  with ev3devcmd package if you have a different 
setup for the ev3 brick. You can configure this with the three environment 
variables **EV3IP**, **EV3USERNAME** and **EV3PASSWORD**.


# ev3dev command-line program

The ev3dev command-line program uses the ev3devcmd library to make it possible to upload/start/download/delete/cleanup programs from the EV3 using a command shell on your PC.

The ev3dev command-line programs support for each action of upload/start/download/delete a sub-command.

To list all sub-commands run:

    $ ev3dev --help
    usage: ev3dev [-h] [-a ADDRESS] [-u USERNAME] [-p PASSWORD]
                  {list,upload,download,delete,cleanup,mirror,start,stop,install_logging,install_rpyc_server}
                  ...

    Commands to upload/start/download/delete/cleanup programs on the EV3
    Complete documentation at: https://github.com/ev3dev-python-tools/ev3devcmd/

    positional arguments:
      {list,upload,download,delete,cleanup,mirror,start,stop,install_logging,install_rpyc_server}
        list                list all files in homedir on EV3
        upload              upload file to homedir on EV3
        download            download file from homedir on EV3
        delete              delete a file in homedir on EV3
        cleanup             delete all files in homedir on EV3
        mirror              mirror sourcedir into homedir on EV3. Also subdirs are
                            mirrored, and all other files within homedir but not
                            in sourcedir are removed.
        start               start program on EV3; program must already be on EV3's
                            homedir
        stop                stop program/motors/sound on EV3
        install_logging     install ev3devlogging package on the EV3 when just
                            having installed a newly installed ev3dev image
        install_rpyc_server
                            install rpyc server on the EV3 when just having
                            installed a newly installed ev3dev image

    optional arguments:
      -h, --help            show this help message and exit
      -a ADDRESS, --address ADDRESS
                            network address of EV3. Can also be set with EV3IP
                            environment variable.
      -u USERNAME, --username USERNAME
                            username used to login with ssh on EV3. Can also be
                            set with EV3USERNAME environment variable.
      -p PASSWORD, --password PASSWORD
                            password used to login with ssh on EV3. Can also be
                            set with EV3PASSWORD environment variable.

To list help for a specific sub-command use the '--help' option after the sub-command. Eg.

    $ ev3dev upload --help
    usage: ev3dev upload [-h] [-f] file
    
    upload file to homedir on EV3
    
    positional arguments:
      file         source path on pc; destination path on EV3 is
                   /home/USERNAME/basename(file)
    
    optional arguments:
      -h, --help   show this help message and exit
      -f, --force  overwrite file if already exist

 

