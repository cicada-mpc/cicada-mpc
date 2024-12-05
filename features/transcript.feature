Feature: Transcripts

    Scenario: Network Transcripts
        Given 2 players
        When received message transcription is enabled and player 0 broadcasts "foo"
        Then the transcript for player 0 should match "Player 0: <-- 0 BROADCAST foo\n"
        And the transcript for player 1 should match "Player 1: <-- 0 BROADCAST foo\n"


#    Scenario: Change Sync Permanently
#        Given 3 players
#        When the players create a Cicada logger, they can change the sync attribute
#
#
#    Scenario: Change Sync Temporarily
#        Given 3 players
#        When the players create a Cicada logger, they can temporarily change the sync attribute
#
#
#    Scenario Outline: Message Logging
#        Given <players> players
#        When the players log <message> with level <level> and src <src>, the message is logged correctly
#
#        Examples:
#        | players | message | level            | src       |
#        | 2       | "foo"   | logging.DEBUG    | None      |
#        | 3       | "bar"   | logging.INFO     | 0         |
#        | 4       | "blah"  | logging.WARNING  | [1]       |
#        | 5       | "bleh"  | logging.ERROR    | [2, 3]    |
#        | 6       | "bleh"  | logging.CRITICAL | None      |
