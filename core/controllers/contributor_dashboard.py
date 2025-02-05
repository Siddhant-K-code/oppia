# Copyright 2019 The Oppia Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Controllers for the contributor dashboard page."""

from __future__ import absolute_import  # pylint: disable=import-only-modules
from __future__ import unicode_literals  # pylint: disable=import-only-modules

from constants import constants
from core.controllers import acl_decorators
from core.controllers import base
from core.domain import config_domain
from core.domain import exp_fetchers
from core.domain import opportunity_services
from core.domain import suggestion_services
from core.domain import topic_fetchers
from core.domain import user_services
import feconf
import utils


class ContributorDashboardPage(base.BaseHandler):
    """Page showing the contributor dashboard."""

    @acl_decorators.open_access
    def get(self):
        # TODO(#7402): Serve this page statically through app.yaml once
        # the CONTRIBUTOR_DASHBOARD_ENABLED flag is removed.
        if not config_domain.CONTRIBUTOR_DASHBOARD_IS_ENABLED.value:
            raise self.PageNotFoundException
        self.render_template('contributor-dashboard-page.mainpage.html')


class ContributionOpportunitiesHandler(base.BaseHandler):
    """Provides data for opportunities available in different categories."""

    GET_HANDLER_ERROR_RETURN_TYPE = feconf.HANDLER_TYPE_JSON

    @acl_decorators.open_access
    def get(self, opportunity_type):
        """Handles GET requests.
        Args:
            opportunity_type: str. Type of Opportunity.
        """
        if not config_domain.CONTRIBUTOR_DASHBOARD_IS_ENABLED.value:
            raise self.PageNotFoundException
        search_cursor = self.request.get('cursor', None)

        if opportunity_type == constants.OPPORTUNITY_TYPE_SKILL:
            opportunities, next_cursor, more = (
                self._get_skill_opportunities_with_corresponding_topic_name(
                    search_cursor))

        elif opportunity_type == constants.OPPORTUNITY_TYPE_TRANSLATION:
            language_code = self.request.get('language_code')
            if language_code is None or not (
                    utils.is_supported_audio_language_code(language_code)):
                raise self.InvalidInputException
            opportunities, next_cursor, more = (
                self._get_translation_opportunity_dicts(
                    language_code, search_cursor))

        elif opportunity_type == constants.OPPORTUNITY_TYPE_VOICEOVER:
            language_code = self.request.get('language_code')
            if language_code is None or not (
                    utils.is_supported_audio_language_code(language_code)):
                raise self.InvalidInputException
            opportunities, next_cursor, more = (
                self._get_voiceover_opportunity_dicts(
                    language_code, search_cursor))

        else:
            raise self.PageNotFoundException

        self.values = {
            'opportunities': opportunities,
            'next_cursor': next_cursor,
            'more': more
        }

        self.render_json(self.values)

    def _get_skill_opportunities_with_corresponding_topic_name(self, cursor):
        """Returns a list of skill opportunities available for questions with
        topic information.

        Args:
            cursor: str or None. If provided, the list of returned entities
                starts from this datastore cursor. Otherwise, the returned
                entities start from the beginning of the full list of entities.

        Returns:
            3-tuple(opportunities, cursor, more). where:
                opportunities: list(dict). A list of dicts of skill opportunity
                    details with additional corresponding topic_name.
                cursor: str or None. A query cursor pointing to the next
                    batch of results. If there are no more results, this might
                    be None.
                more: bool. If True, there are (probably) more results after
                    this batch. If False, there are no further results after
                    this batch.
        """
        topics_with_skills = topic_fetchers.get_all_topics_with_skills()
        skill_opportunities, cursor, more = (
            opportunity_services.get_skill_opportunities(cursor))
        id_to_skill_opportunity_dict = {
            opp.id: opp.to_dict() for opp in skill_opportunities}
        opportunities = []
        for topic in topics_with_skills:
            for skill_id in topic.get_all_skill_ids():
                if len(opportunities) == constants.OPPORTUNITIES_PAGE_SIZE:
                    break
                if skill_id in id_to_skill_opportunity_dict:
                    skill_opportunity_dict = (
                        id_to_skill_opportunity_dict[skill_id])
                    skill_opportunity_dict['topic_name'] = topic.name
                    opportunities.append(skill_opportunity_dict)
        return opportunities, cursor, more

    def _get_translation_opportunity_dicts(self, language_code, search_cursor):
        """Returns a list of translation opportunity dicts.

        Args:
            language_code: str. The language for which translation opportunities
                should be fetched.
            search_cursor: str or None. If provided, the list of returned
                entities starts from this datastore cursor. Otherwise, the
                returned entities start from the beginning of the full list of
                entities.

        Returns:
            3-tuple(opportunities, cursor, more). where:
            opportunities: list(dict). A list of ExplorationOpportunitySummary
                dicts.
            cursor: str or None. A query cursor pointing to the next batch of
                results. If there are no more results, this might be None.
            more: bool. If True, there are (probably) more results after this
                batch. If False, there are no further results after this batch.
        """
        opportunities, next_cursor, more = (
            opportunity_services.get_translation_opportunities(
                language_code, search_cursor))
        opportunity_dicts = [opp.to_dict() for opp in opportunities]
        return opportunity_dicts, next_cursor, more

    def _get_voiceover_opportunity_dicts(self, language_code, search_cursor):
        """Returns a list of voiceover opportunity dicts.

        Args:
            language_code: str. The language for which voiceover opportunities
                should be fetched.
            search_cursor: str or None. If provided, the list of returned
                entities starts from this datastore cursor. Otherwise, the
                returned entities start from the beginning of the full list of
                entities.

        Returns:
            3-tuple(opportunities, cursor, more). where:
            opportunities: list(dict). A list of ExplorationOpportunitySummary
                dicts.
            cursor: str or None. A query cursor pointing to the next batch of
                results. If there are no more results, this might be None.
            more: bool. If True, there are (probably) more results after this
                batch. If False, there are no further results after this batch.
        """
        opportunities, next_cursor, more = (
            opportunity_services.get_voiceover_opportunities(
                language_code, search_cursor))
        opportunity_dicts = [opp.to_dict() for opp in opportunities]
        return opportunity_dicts, next_cursor, more


class TranslatableTextHandler(base.BaseHandler):
    """Provides lessons content which can be translated in a given language."""

    GET_HANDLER_ERROR_RETURN_TYPE = feconf.HANDLER_TYPE_JSON

    @acl_decorators.open_access
    def get(self):
        """Handles GET requests."""
        language_code = self.request.get('language_code')
        exp_id = self.request.get('exp_id')

        if not utils.is_supported_audio_language_code(language_code):
            raise self.InvalidInputException('Invalid language_code: %s' % (
                language_code))

        if not opportunity_services.is_exploration_available_for_contribution(
                exp_id):
            raise self.InvalidInputException('Invalid exp_id: %s' % exp_id)

        exp = exp_fetchers.get_exploration_by_id(exp_id)
        state_names_to_content_id_mapping = exp.get_translatable_text(
            language_code)
        state_names_to_not_in_review_content_id_mapping = (
            self._get_state_names_to_not_in_review_content_id_mapping(
                state_names_to_content_id_mapping,
                suggestion_services
                .get_translation_suggestions_in_review_by_exploration(exp_id)
            )
        )

        self.values = {
            'state_names_to_content_id_mapping': (
                state_names_to_not_in_review_content_id_mapping),
            'version': exp.version
        }

        self.render_json(self.values)

    def _get_state_names_to_not_in_review_content_id_mapping(
            self, state_names_to_content_id_mapping, suggestions):
        """Returns a copy of the supplied state_names_to_content_id_mapping
        minus any contents found in suggestions.

        Args:
            state_names_to_content_id_mapping: dict(str, dict(str, str)). A dict
                where state_name is the key and a dict with content_id as the
                key and html content as value.
            suggestions: list(Suggestion). A list of translation suggestions.

        Returns:
            dict(str, dict(str, str)). A dict where state_name is the key and a
            dict with content_id as the key and html content as value.
        """
        final_mapping = {}
        for state_name in state_names_to_content_id_mapping:
            content_id_to_text = dict(
                state_names_to_content_id_mapping[state_name])
            for content_id in content_id_to_text.keys():
                if self._content_in_review(state_name, content_id, suggestions):
                    del content_id_to_text[content_id]
            if content_id_to_text:
                final_mapping[state_name] = content_id_to_text
        return final_mapping

    def _content_in_review(self, state_name, content_id, suggestions):
        """Returns whether a suggestion exists in suggestions with a change dict
        matching the supplied state_name and content_id.

        Args:
            state_name: str. Exploration state name.
            content_id: str. Content ID.
            suggestions: list(Suggestion). A list of translation suggestions.

        Returns:
            bool. True if suggestion exists in suggestions with a change dict
            matching state_name and content_id, False otherwise.
        """
        return any(
            s.change.state_name == state_name and
            s.change.content_id == content_id for s in suggestions)


class UserContributionRightsDataHandler(base.BaseHandler):
    """Provides contribution rights of the logged in user in translation,
    voiceover and question category on the contributor dashboard.
    """

    GET_HANDLER_ERROR_RETURN_TYPE = feconf.HANDLER_TYPE_JSON

    @acl_decorators.open_access
    def get(self):
        """Handles GET requests."""
        contribution_rights = None
        if self.username:
            contribution_rights = user_services.get_user_contribution_rights(
                self.user_id)
        self.render_json({
            'can_review_translation_for_language_codes': (
                contribution_rights.can_review_translation_for_language_codes
                if contribution_rights else []),
            'can_review_voiceover_for_language_codes': (
                contribution_rights.can_review_voiceover_for_language_codes
                if contribution_rights else []),
            'can_review_questions': (
                contribution_rights.can_review_questions
                if contribution_rights else False),
            'can_suggest_questions': (
                config_domain.CONTRIBUTOR_CAN_SUGGEST_QUESTIONS.value and
                (contribution_rights.can_submit_questions
                 if contribution_rights else False))
        })


class FeaturedTranslationLanguagesHandler(base.BaseHandler):
    """Provides featured translation languages set in admin config."""

    GET_HANDLER_ERROR_RETURN_TYPE = feconf.HANDLER_TYPE_JSON

    @acl_decorators.open_access
    def get(self):
        """Handles GET requests."""
        self.render_json({
            'featured_translation_languages':
                config_domain.FEATURED_TRANSLATION_LANGUAGES.value
        })
