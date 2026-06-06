#!/bin/bash

SECONDS=0

unzip dataset.zip

WORKING_DIR=$(pwd)

#DRIVERS_LIST=()
#DRIVERS_LIST=("DocChecker" "Baseline" "C4RLLaMA")
DRIVERS_LIST=("Baseline")

#  alter the drivers list to run the specific drivers you want, if the list is empty, it will run all the drivers in the drivers folder

(
cd java
for repo in */*
do
(
	echo "At repository: $repo ---------------------"
	cd "$repo"
	# clone this repo once; subsequent commits patch and revert it in place
	git clone https://github.com/$repo ./repository
	export REPO_PATH="$(pwd)/repository"

	for commit in *
	do

		if [ $commit == "repository" ]
		then continue
		fi

	(
		echo "    At commit: $commit -------"

		# revert any leftover state from the previous commit and check out the new one
		(cd repository; git reset --hard HEAD; git clean -fdx; git checkout $commit)

		# apply patch directly to the cloned repo (no backup copy)
		(cd repository; patch -p1 -f < "../$commit/file.patch")

		cd "$commit"

		for num in *
		do
			if [[ $num == "file.patch" ]]
			then continue
			fi
		(
			echo "        At number: $num"

			cd $WORKING_DIR/drivers
			if [ ${#DRIVERS_LIST[@]} -eq 0 ]; then
				drivers_to_run=(*)
		  	else
				drivers_to_run=("${DRIVERS_LIST[@]}")
			fi

			for driver in "${drivers_to_run[@]}";
			do
			(
				echo "copy $driver"

				# copy the driver folder and the analyzed.json; the repository is shared via $REPO_PATH
				cp -r $driver "../java/$repo/$commit/$num/$driver"
				cd "../java/$repo/$commit/$num"
				cp "./analyzed.json" "./$driver/analyzed.json"
				cd "./$driver"

				bash driver.sh

				mv "result.txt" "../result_$driver.txt"
				mv "log.txt" "../log_$driver.txt"
				mv "errors.txt" "../errors_$driver.txt"

				cp "analyzed.json" "../analyzed.json"
				#  -----------

				cd ..
				rm -rf $driver
			)
			done
		)
		done
		# echo Press to continue
		# read
	)
	done
	rm -rf ./repository
)
done
(cd; cd "CASCADE"; git rev-parse HEAD >> $WORKING_DIR/runs; date >> $WORKING_DIR/runs;  echo >> $WORKING_DIR/runs)
)

printf 'Finished in %d h %02d m %02d s\n' $((SECONDS/3600)) $(((SECONDS/60)%60)) $((SECONDS%60))
