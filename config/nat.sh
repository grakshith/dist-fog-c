#! /bin/bash

WLAN_IP=$(ip addr show wlo1 | sed  -rn '/\binet\b/p' | awk '{print $2}' | sed  -n 's/\/[0-9][0-9]//p')

iptables -t nat -A POSTROUTING -o wlo1 -j SNAT --to-source $WLAN_IP


