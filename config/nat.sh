#! /bin/bash

IFACE=wlo1

WLAN_IP=$(ip addr show $IFACE | sed  -rn '/\binet\b/p' | awk '{print $2}' | sed  -n 's/\/[0-9][0-9]//p')

#WLAN_IP=192.168.42.143

iptables -t nat -A POSTROUTING -o $IFACE -j SNAT --to-source $WLAN_IP

#iptables -t nat -A PREROUTING -i wlo1 -j DNAT --to-destination 192.168.1.100
