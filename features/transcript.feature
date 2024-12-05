Feature: Transcripts

    Scenario: Broadcast sent message transcripts
        Given 2 players
        And a network message handler capturing sent messages
        When transcription is enabled and player 0 broadcasts "foo"
        Then the transcript for player 0 should match "Player 0: --> 0 BROADCAST foo\nPlayer 0: --> 1 BROADCAST foo\n"
        And the transcript for player 1 should match ""

    Scenario: Broadcast received message transcripts
        Given 2 players
        And a network message handler capturing received messages
        When transcription is enabled and player 0 broadcasts "foo"
        Then the transcript for player 0 should match "Player 0: <-- 0 BROADCAST foo\n"
        And the transcript for player 1 should match "Player 1: <-- 0 BROADCAST foo\n"


