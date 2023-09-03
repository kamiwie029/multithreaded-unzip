# Basic Multithreaded Unzipper

## Test file info:
Size: 6,68 GB

Files: 2,635

Folders: 11

Compression ratio: 90%

## Speeds:
This script (~30 runs):
AVG 17.578632831573486

Windows Unzip (3 runs):
AVG 2 minutes 15 seconds

7zip (5 runs):
AVG 56 seconds

## Notes:
This was tested on an M.2 drive. This will most likely not work on HDDs because they're not able to access different portions in parallel.
You can change the no. of threads used for unzipping by changing the `THREAD_LIMIT` const. Running more threads might not lead to better results.
The UI uses 2 threads. There's a warning if you exceed the no. of your CPU threads (`THREAD_LIMIT` +2) but it shouldn't affect the performance much. Due to the task being I/O I recommend running 4 threads.

The performance will vary between different archives. E.g. When running 4 threads, an archive with one 10GB file and three 50MB files will not see much of a difference, as the 3 threads will not be doing any work after they finish unzipping their 50MB file. 

The progress bar tracks unzipped files, meaning, if we have some large files in the archive, at first it will move very slowly and speed up as it moves to smaller files (it unzipps from largest to smallest files). 


