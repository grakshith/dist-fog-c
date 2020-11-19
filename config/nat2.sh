#! /bin/bash

iptables -A FORWARD -i wlo1 -o eno1 -p tcp --syn --dport 8080 -m conntrack --ctstate NEW -j ACCEPT

iptables -A FORWARD -i wlo1 -o eno1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -i eno1 -o wlo1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

iptables -t nat -A PREROUTING -i wlo1 -p tcp --dport 8080 -j DNAT --to-destination 192.168.1.100:8080
iptables -t nat -A POSTROUTING -o eth0 -p tcp --dport 8080 -d 192.168.1.100 -j SNAT --to-source 192.168.1.1

