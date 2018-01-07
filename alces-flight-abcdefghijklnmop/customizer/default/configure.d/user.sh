#!/bin/bash

user="AWSusername"

pubkey="ssh-rsa AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

file=/home/${user}/.ssh/authorized_keys

if [ -f ${file} ]; then
   #echo "File $file exists."
   x=$( grep $user $file )
   if [[ -z $x ]]; then
      echo "${pubkey} ${user}" >> ${file}
   fi
else
   echo "File $file does not exist."
fi

touch /tmp/user-script-run
