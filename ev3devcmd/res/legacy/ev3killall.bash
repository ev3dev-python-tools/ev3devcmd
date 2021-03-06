
 printf "kill programs running on EV3\n"
 # kill programs running on ev3
 pid=`pgrep -f 'python3 /home/robot'`
 if [[ -n $pid ]]; then kill -9 -$pid; fi

 printf "stop motors on EV3\n"
 # kill motors
 python3 -c "exec(\"import ev3dev.ev3\nfor m in ev3dev.ev3.list_motors():\n  m.reset()\")"

 printf "stop sound on EV3\n"
 # kill sound via beep
 sudo  pkill -f /usr/bin/aplay

 # kill sound aplay
 sudo pkill -f /usr/bin/beep

 printf "set leds back to default of green\n"
 python3 -c "exec(\"import ev3dev.ev3\nev3dev.ev3.Leds.set_color(ev3dev.ev3.Leds.LEFT, ev3dev.ev3.Leds.GREEN)\nev3dev.ev3.Leds.set_color(ev3dev.ev3.Leds.RIGHT, ev3dev.ev3.Leds.GREEN)\")"
 exit
