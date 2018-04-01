#! /bin/bash

WLAN_IP=$(ip addr show wlp4s0 | sed  -rn '/\binet\b/p' | awk '{print $2}' | sed  -n 's/\/[0-9][0-9]//p')

iptables -t nat -A POSTROUTING -o wlp4s0 -j SNAT --to-source $WLAN_IP


