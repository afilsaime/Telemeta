#!/bin/sh

for file in `ls $1/*.sh`; do
sudo perl -pi -e 's/threads=2/threads=8/g' $1/$file 
sudo perl -pi -e 's/threads=4/threads=8/g' $1/$file
sudo perl -pi -e 's/threads=6/threads=8/g' $1/$file
done
