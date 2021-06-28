Feature: Shamir Protocol

    Scenario: Inter-session Repetition
        Given 5 players
        And a minimum of 3 shares to recover a secret
        When shamir secret sharing the same value for 10 sessions
	    Then the shares should never be repeated


	Scenario: Intra-session Repetition
        Given 5 players
        And a minimum of 3 shares to recover a secret
        When shamir secret sharing the same value 10 times in one session
        Then the shares should never be repeated


    Scenario Outline: Secret sharing
        Given <players> players
        And a minimum of <k> shares to recover a secret
        When player <player> shamir shares <secret> with <recipients> and <senders> reveal their shares to <destinations>
        Then the group should return <result>

        Examples:
        | players | k | player | secret        | recipients | senders | destinations | result                |
        | 2       | 2 | 0      | 13            | None       | None    | None         | [13] * 2              |
        | 2       | 2 | 1      | 13            | None       | None    | None         | [13] * 2              |
        | 3       | 3 | 2      | 13            | None       | None    | None         | [13] * 3              |
        | 3       | 2 | 2      | 13            | None       | None    | None         | [13] * 3              |
        | 3       | 2 | 2      | [1,2]         | None       | None    | None         | [[1,2]] * 3           |
        | 3       | 2 | 2      | [1,2,3]       | None       | None    | None         | [[1,2,3]] * 3         |
        | 3       | 2 | 2      | [[1,2],[3,4]] | None       | None    | None         | [[[1,2],[3,4]]] * 3   |
        | 3       | 2 | 0      | 13            | None       | None    | [0]          | [13, None, None]      |
        | 3       | 2 | 0      | 13            | None       | [1, 2]  | [0]          | [13, None, None]      |
        | 3       | 2 | 0      | 13            | None       | [1, 2]  | [1]          | [None, 13, None]      |
        | 3       | 2 | 0      | 13            | None       | [1, 2]  | [1, 2]       | [None, 13, 13]        |
        | 3       | 2 | 0      | 13            | [1, 2]     | [1, 2]  | [0]          | [13, None, None]      |
        | 3       | 2 | 0      | 13            | [1, 2]     | [1, 2]  | [1]          | [None, 13, None]      |
        | 3       | 2 | 0      | 13            | [1, 2]     | [1, 2]  | [0, 2]       | [13, None, 13]        |
