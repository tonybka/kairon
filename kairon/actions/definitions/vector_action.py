from typing import Text, Dict, Any

from loguru import logger
from mongoengine import DoesNotExist
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

from kairon.actions.definitions.base import ActionsBase
from kairon.shared.actions.data_objects import ActionServerLogs
from kairon.shared.actions.data_objects import VectorEmbeddingDbAction
from kairon.shared.actions.exception import ActionFailure
from kairon.shared.actions.models import ActionType, VectorDbValueType
from kairon.shared.actions.utils import ActionUtility
from kairon.shared.constants import KaironSystemSlots
from kairon.shared.vector_embeddings.db.factory import VectorEmbeddingsDbFactory


class VectorEmbeddingsDbAction(ActionsBase):

    def __init__(self, bot: Text, name: Text):
        """
        Initialize Email action.

        @param bot: bot id
        @param name: action name
        """
        self.bot = bot
        self.name = name
        self.__response = None
        self.__is_success = False

    def retrieve_config(self):
        """
        Fetch Vector action configuration parameters from the database.

        :return: VectorEmbeddingDbAction containing configuration for the action as dict.
        """
        try:
            vector_action_dict = VectorEmbeddingDbAction.objects(bot=self.bot, name=self.name,
                                                                 status=True).get().to_mongo().to_dict()
            logger.debug("vector_action_config: " + str(vector_action_dict))
            return vector_action_dict
        except DoesNotExist as e:
            logger.exception(e)
            raise ActionFailure("No Vector action found for given action and bot")

    async def execute(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        """
        Retrieves action config and executes it.
        Information regarding the execution is logged in ActionServerLogs.

        @param dispatcher: Client to send messages back to the user.
        @param tracker: Tracker object to retrieve slots, events, messages and other contextual information.
        @param domain: Bot domain
        :return: Dict containing slot name as keys and their values.
        """
        vector_action_config = None
        response = None
        bot_response = None
        exception = None
        status = "SUCCESS"
        dispatch_bot_response = False
        failure_response = 'I have failed to process your request.'
        filled_slots = {}
        msg_logger = []

        try:
            vector_action_config = self.retrieve_config()
            dispatch_bot_response = vector_action_config['response']['dispatch']
            failure_response = vector_action_config['failure_response']
            collection_name = vector_action_config['collection']
            db_type = vector_action_config['db_type']
            vector_db = VectorEmbeddingsDbFactory.get_instance(db_type)(collection_name)
            operation_type = vector_action_config['operation']
            payload_type = vector_action_config['payload']
            request_body = tracker.get_slot(payload_type.get('value')) if payload_type.get('type') == VectorDbValueType.from_slot.value \
                else payload_type.get('value')
            msg_logger.append(request_body)
            tracker_data = ActionUtility.build_context(tracker, True)
            response = vector_db.perform_operation(operation_type.get('value'), request_body)
            logger.info("response: " + str(response))
            response_context = self.__add_user_context_to_http_response(response, tracker_data)
            bot_response, bot_resp_log = ActionUtility.compose_response(vector_action_config['response'], response_context)
            msg_logger.append(bot_resp_log)
            slot_values, slot_eval_log = ActionUtility.fill_slots_from_response(vector_action_config.get('set_slots', []),
                                                                                response_context)
            msg_logger.extend(slot_eval_log)
            filled_slots.update(slot_values)
            logger.info("response: " + str(bot_response))
        except Exception as e:
            exception = str(e)
            logger.exception(e)
            status = "FAILURE"
            bot_response = failure_response
        finally:
            if dispatch_bot_response:
                dispatcher.utter_message(bot_response)
            ActionServerLogs(
                type=ActionType.vector_embeddings_db_action.value,
                intent=tracker.get_intent_of_latest_message(skip_fallback_intent=False),
                action=self.name,
                config=vector_action_config,
                sender=tracker.sender_id,
                response=str(response) if response else None,
                bot_response=str(bot_response) if bot_response else None,
                messages=msg_logger,
                exception=exception,
                bot=self.bot,
                status=status,
                user_msg=tracker.latest_message.get('text')
            ).save()
        filled_slots.update({KaironSystemSlots.kairon_action_response.value: bot_response})
        return filled_slots

    @staticmethod
    def __add_user_context_to_http_response(http_response, tracker_data):
        response_context = {"data": http_response, 'context': tracker_data}
        return response_context

