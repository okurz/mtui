#!/bin/sh
HOSTS=$@

if [ ! -z $KDE_SESSION_VERSION ]; then
        if [ $KDE_SESSION_VERSION -eq 4 ]; then
                if [ "$MTUI_USE_CURRENT_KONSOLE" == yes ] ; then
                        K_DBUS_SRV=$KONSOLE_DBUS_SERVICE
                else
                        /usr/bin/konsole --nofork&
                        pid=$!
                        K_DBUS_SRV=org.kde.konsole-$pid
                        sleep 3
                        session_num=1
                        qdbus $K_DBUS_SRV /Sessions/$session_num sendText "ssh -Y root@$1"
                        sleep 1
                        qdbus $K_DBUS_SRV /Sessions/$session_num sendText $'
'
                        shift
                fi
                while [ $# -gt 0 ] ; do
                        session_num=`qdbus $K_DBUS_SRV /Konsole newSession`
                        sleep 1
                        qdbus $K_DBUS_SRV /Sessions/$session_num sendText "ssh -Y root@$1"
                        shift
                        sleep 1
                        qdbus $K_DBUS_SRV /Sessions/$session_num sendText $'
'
                done
        fi
else
        # must be KDE < 4
        /opt/kde3/bin/konsole --script &
        KONSOLE=konsole-$!
        sleep 3
        for i in $HOSTS; do
           SESSION=`dcop $KONSOLE 'konsole' newSession`
           sleep 1
           dcop $KONSOLE $SESSION renameSession $i
           sleep 1
           dcop $KONSOLE $SESSION sendSession "ssh -Y root@$i"
        done
fi


