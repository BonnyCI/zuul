#!/usr/bin/env python

# Copyright (c) 2016 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

from tests.base import ZuulTestCase

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-32s '
                    '%(levelname)-8s %(message)s')


class TestGithubRequirements(ZuulTestCase):
    """Test pipeline and trigger requirements"""

    def setup_config(self, config_file='zuul-github.conf'):
        super(TestGithubRequirements, self).setup_config(config_file)

    def test_pipeline_require_status(self):
        "Test pipeline requirement: status"
        self.config.set('zuul', 'layout_config',
                        'tests/fixtures/layout-github-requirement-status.yaml')
        self.sched.reconfigure(self.config)
        self.registerJobs()

        A = self.fake_github.openFakePullRequest('org/project1', 'master', 'A')
        # A comment event that we will keep submitting to trigger
        comment = A.getCommentAddedEvent('test me')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        # No status from zuul so should not be enqueued
        self.assertEqual(len(self.history), 0)

        # An error status should not cause it to be enqueued
        A.setStatus(A.head_sha, 'error', 'null', 'null', 'check')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 0)

        # A success status goes in
        A.setStatus(A.head_sha, 'success', 'null', 'null', 'check')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 1)
        self.assertEqual(self.history[0].name, 'project1-pipeline')

    def test_trigger_require_status(self):
        "Test trigger requirement: status"
        self.config.set('zuul', 'layout_config',
                        'tests/fixtures/layout-github-requirement-status.yaml')
        self.sched.reconfigure(self.config)
        self.registerJobs()

        A = self.fake_github.openFakePullRequest('org/project2', 'master', 'A')

        # An error status should not cause it to be enqueued
        A.setStatus(A.head_sha, 'error', 'null', 'null', 'check')
        self.fake_github.emitEvent(A.getCommitStatusEvent('error'))
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 0)

        # A success status from unknown user should not cause it to be
        # enqueued
        A.setStatus(A.head_sha, 'success', 'null', 'null', 'check', user='foo')
        self.fake_github.emitEvent(A.getCommitStatusEvent('error'))
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 0)

        # A success status from zuul goes in
        A.setStatus(A.head_sha, 'success', 'null', 'null', 'check')
        self.fake_github.emitEvent(A.getCommitStatusEvent('success'))
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 1)
        self.assertEqual(self.history[0].name, 'project2-trigger')

# TODO: Implement reject on status

    def test_pipeline_require_approval_username(self):
        "Test pipeline requirement: approval username"
        return self._test_require_approval_username('org/project1',
                                                    'project1-pipeline')


#    def test_trigger_require_approval_username(self):
#        "Test pipeline requirement: approval username"
#        return self._test_require_approval_username('org/project2',
#                                                    'project2-trigger')

    def _test_require_approval_username(self, project, job):
        self.config.set(
            'zuul', 'layout_config',
            'tests/fixtures/layout-github-requirement-username.yaml')
        self.sched.reconfigure(self.config)
        self.registerJobs()

        A = self.fake_github.openFakePullRequest(project, 'master', 'A')
        # A comment event that we will keep submitting to trigger
        comment = A.getCommentAddedEvent('test me')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        # No approval from derp so should not be enqueued
        self.assertEqual(len(self.history), 0)

        # Add an approval (review) from derp
        A.addReview('derp', 'APPROVE')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 1)
        self.assertEqual(self.history[0].name, job)

    def test_pipeline_require_approval_state(self):
        "Test pipeline requirement: approval state"
        return self._test_require_approval_state('org/project1',
                                                 'project1-pipeline')

#    def test_trigger_require_approval_state(self):
#        "Test pipeline requirement: approval state"
#        return self._test_require_approval_state('org/project2',
#                                                 'project2-trigger')

    def _test_require_approval_state(self, project, job):
        self.config.set('zuul', 'layout_config',
                        'tests/fixtures/layout-github-requirement-state.yaml')
        self.sched.reconfigure(self.config)
        self.registerJobs()

        A = self.fake_github.openFakePullRequest(project, 'master', 'A')
        # Add derp to writers
        A.writers.append('derp')
        # A comment event that we will keep submitting to trigger
        comment = A.getCommentAddedEvent('test me')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        # No positive approval from derp so should not be enqueued
        self.assertEqual(len(self.history), 0)

        # A -2 from derp should not cause it to be enqueued
        A.addReview('derp', 'REQUEST_CHANGES')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 0)

        # A +1 from nobody should not cause it to be enqueued
        A.addReview('nobody', 'APPROVE')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 0)

        # A +2 from derp should cause it to be enqueued
        A.addReview('derp', 'APPROVE')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 1)
        self.assertEqual(self.history[0].name, job)

    def test_pipeline_require_approval_user_state(self):
        "Test pipeline requirement: approval state from user"
        return self._test_require_approval_user_state('org/project1',
                                                      'project1-pipeline')

#    def test_trigger_require_approval_user_state(self):
#        "Test pipeline requirement: approval state from user"
#        return self._test_require_approval_user_state('org/project2',
#                                                      'project2-trigger')

    def _test_require_approval_user_state(self, project, job):
        self.config.set(
            'zuul', 'layout_config',
            'tests/fixtures/layout-github-requirement-username-state.yaml')
        self.sched.reconfigure(self.config)
        self.registerJobs()

        A = self.fake_github.openFakePullRequest(project, 'master', 'A')
        # Add derp and herp to writers
        A.writers.extend(('derp', 'herp'))
        # A comment event that we will keep submitting to trigger
        comment = A.getCommentAddedEvent('test me')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        # No positive approval from derp so should not be enqueued
        self.assertEqual(len(self.history), 0)

        # A -2 from derp should not cause it to be enqueued
        A.addReview('derp', 'REQUEST_CHANGES')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 0)

        # A +1 from nobody should not cause it to be enqueued
        A.addReview('nobody', 'APPROVE')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 0)

        # A +2 from herp should not cause it to be enqueued
        A.addReview('herp', 'APPROVE')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 0)

        # A +2 from derp should cause it to be enqueued
        A.addReview('derp', 'APPROVE')
        self.fake_github.emitEvent(comment)
        self.waitUntilSettled()
        self.assertEqual(len(self.history), 1)
        self.assertEqual(self.history[0].name, job)

# TODO: Implement reject on approval username/state
