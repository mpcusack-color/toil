# Copyright (C) 2015-2017 Regents of the University of California
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid
import random

from toil.test import ToilTest, needs_mesos


@needs_mesos
class DataStructuresTest(ToilTest):

    def _getJob(self, cores=1, memory=1000, disk=5000, preemptable=True):
        from toil.batchSystems.mesos import ResourceRequirement
        from toil.batchSystems.mesos import ToilJob

        resources = ResourceRequirement(cores=cores, memory=memory, disk=disk, preemptable=preemptable)

        job = ToilJob(jobID=str(uuid.uuid4()),
                      name=str(uuid.uuid4()),
                      resources=resources,
                      command="do nothing",
                      userScript=None,
                      environment=None,
                      workerCleanupInfo=None)
        return job

    def testJobQueue(self, testJobs=1000):
        from toil.batchSystems.mesos import JobQueue
        jobQueue = JobQueue()

        for jobNum in range(0, testJobs):
            testJob = self._getJob(cores=random.choice(range(10)), preemptable=random.choice([True, False]))
            jobQueue.insertJob(testJob, testJob.resources)

        sortedTypes = jobQueue.sorted()
        # test this is properly sorted
        assert len(sortedTypes) <= 20
        assert all(sortedTypes[i] <= sortedTypes[i + 1] for i in range(len(sortedTypes) - 1))

        preemptable = sortedTypes.pop(0).preemptable
        for jtype in sortedTypes:
            # all non preemptable jobTypes must be first in sorted order
            if preemptable:
                # all the rest of the jobTypes must be preemptable as well
                assert jtype.preemptable
            elif jtype.preemptable:
                # we have reached our first preemptable job
                preemptable = jtype.preemptable

        # make sure proper number of jobs are in queue
        assert len(jobQueue.jobIDs()) == testJobs

        testJob = self._getJob(cores=random.choice(1, 10))
        jobQueue.insertJob(testJob, testJob.resources)
        testJobs += 1

        assert len(jobQueue.jobIDs()) == testJobs
        assert testJobs >= len(jobQueue.jobsOfType(testJob.resources)) >= 1

        jobsRemoved = 0
        while len(jobQueue.jobsOfType(testJob.resources)) > 1:
            jobsRemoved += 1
            jobQueue.nextJobOfType(testJob.resources)

        testJobs -= jobsRemoved
        assert testJobs == len(jobQueue.jobIDs())

        # only most recently added job will be in this queue now - test to insure FIFO
        testJob2 = jobQueue.nextJobOfType(testJob.resources)
        assert testJob is testJob2

