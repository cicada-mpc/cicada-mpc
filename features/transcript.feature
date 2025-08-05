Feature: Transcripts

    Scenario: Broadcast sent message transcripts
        Given 2 players
        And a network message handler capturing sent messages
        When transcription is enabled and player 0 broadcasts "foo"
        Then the transcript for player 0 should match "Player 0: --> 0 BROADCAST foo\nPlayer 0: --> 1 BROADCAST foo"
        And the transcript for player 1 should match ""

    Scenario: Broadcast received message transcripts
        Given 2 players
        And a network message handler capturing received messages
        When transcription is enabled and player 0 broadcasts "foo"
        Then the transcript for player 0 should match "Player 0: <-- 0 BROADCAST foo"
        And the transcript for player 1 should match "Player 1: <-- 0 BROADCAST foo"

    Scenario: Simple code transcripts
        Given 1 player
        And a default code message handler
        When transcription is enabled and player 0 generates an order 127 field array of 3 ones
        Then the player transcripts can be executed without error
        And the transcript for player 0 should match "cicada.transcript.assert_equal(cicada.arithmetic.Field(order=127).ones(shape=3), numpy.array([1, 1, 1], dtype='object'))"

    Scenario: Multidimensional field array transcript formatting
        Given 1 player
        And a default code message handler
        When transcription is enabled and player 0 generates a field array from a numpy array with shape (4, 3)
        Then the player transcripts can be executed without error
        And the transcript for player 0 should match "cicada.transcript.assert_equal(cicada.arithmetic.Field(order=18446744073709551557).__call__(object=numpy.array([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], dtype='int64')), numpy.array([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]], dtype='object'))"

    Scenario: Multidimensional active share transcript formatting
        Given 3 players
        And a default code message handler
        When transcription is enabled while formatting an active share with shape (2, 2)
        Then the player transcripts can be executed without error
        And the transcript for player 0 should match "# cicada.active.ActiveArrayShare(storage=(cicada.additive.AdditiveArrayShare(storage=numpy.array([[5819376713854848603, 396104297408416873], [2191134801812730022, 3514190104655732506]], dtype='object')), cicada.shamir.ShamirArrayShare(storage=numpy.array([[13455549500651079930, 9344100599580480609], [12987499703789640172, 10249869608526413378]], dtype='object')))).__repr__()\n\n# cicada.additive.AdditiveArrayShare(storage=numpy.array([[5819376713854848603, 396104297408416873], [2191134801812730022, 3514190104655732506]], dtype='object')).__repr__()\n\n# cicada.shamir.ShamirArrayShare(storage=numpy.array([[13455549500651079930, 9344100599580480609], [12987499703789640172, 10249869608526413378]], dtype='object')).__repr__()"

    Scenario: Multidimensional additive share transcript formatting
        Given 1 player
        And a default code message handler
        When transcription is enabled while formatting an additive share with shape (2, 2)
        Then the player transcripts can be executed without error
        And the transcript for player 0 should match "# cicada.additive.AdditiveArrayShare(storage=numpy.array([[0, 65536], [131072, 196608]], dtype='object')).__repr__()"

    Scenario: Multidimensional Shamir share transcript formatting
        Given 3 players
        And a default code message handler
        When transcription is enabled while formatting a shamir share with shape (2, 2)
        Then the player transcripts can be executed without error
        And the transcript for player 0 should match "# cicada.shamir.ShamirArrayShare(storage=numpy.array([[13455549500651079930, 9344100599580480609], [12987499703789640172, 10249869608526413378]], dtype='object')).__repr__()"

    Scenario: Shamir absolute transcript formatting
        Given 3 players
        And a default code message handler
        When transcription is enabled while computing an absolute value with shamir sharing
        Then the player transcripts can be executed without error



