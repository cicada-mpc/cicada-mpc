Feature: Additive Protocol

    Scenario Outline: Startup Reliability
        Given <players> players
        Then it should be possible to setup an additive protocol object <count> times

        Examples:
        | players | count   |
        | 2       | 10      |
        | 3       | 10      |
        | 4       | 10      |
        | 10      | 10      |


    Scenario: Inter-session Repetition
        Given 3 players
        When secret sharing the same value for 10 sessions
	    Then the shares should never be repeated


	Scenario: Intra-session Repetition
        Given 3 players
        When secret sharing the same value 10 times in one session
        Then the shares should never be repeated


    Scenario Outline: Random Round Trip Sharing
        Given <players> players
        When player <player> shares and reveals <count> random secrets, the revealed secrets should match the originals

        Examples:
        | players | player | count      |
        | 2       | 0      | 10         |
        | 3       | 1      | 10         |
        | 4       | 2      | 10         |


    Scenario Outline: Local Addition
        Given <players> players
        And secret value <secret>
        And local value <local>
        When player <player> performs local in-place addition on the shared secret
        Then the group should return <result>

        Examples:
        | players | secret  | local       | player | result                                 |
        | 2       | 5       | 1           | 1      | [6] * 2                                |
        | 3       | 5       | 1.1         | 1      | [6.1] * 3                              |
        | 4       | 5       | 1.5         | 2      | [6.5] * 4                              |
        | 3       | [5, 3]  | [1.1, 2.2]  | 1      | [[6.1, 5.2]] * 3                       |


    Scenario Outline: Local Subtraction
        Given <players> players
        And secret value <secret>
        And local value <local>
        When player <player> performs local in-place subtraction on the shared secret
        Then the group should return <result>

        Examples:
        | players | secret  | local       | player | result                                    |
        | 2       | 5       | 1           | 1      | [4] * 2                                   |
        | 3       | 5       | 1.1         | 1      | [3.9] * 3                                 |
        | 4       | 5       | 1.5         | 1      | [3.5] * 4                                 |
        | 3       | [5, 3]  | [1.1, 3.2]  | 1      | [[3.9, -0.2]] * 3                         |


    Scenario Outline: Random Bitwise Secret
        Given <players> players
        Then generating <bits> random bits with players <src> and seed <seed> produces a valid result

        Examples:
        | players | bits  | src       | seed |
        | 2       | 1     | None      | 1234 |
        | 2       | 2     | None      | 1235 |
        | 2       | 4     | None      | 1236 |
        | 2       | 8     | None      | 1237 |
        | 3       | 8     | None      | 1238 |
        | 3       | 8     | None      | 1239 |


    Scenario Outline: Multiplicative Inverse
        Given <players> players
        And unary operation <operation>
        And operand <a>
        When the unary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation             | a                                | count| result                |
        | 2       | multiplicative_inverse| 2                                | 1    | [[1] * 2]             |
        | 2       | multiplicative_inverse| 100                              | 1    | [[1] * 2]             |
        | 2       | multiplicative_inverse| -75                              | 1    | [[1] * 2]             |
        | 2       | multiplicative_inverse| -1000                            | 1    | [[1] * 2]             |
        | 2       | multiplicative_inverse| [[35.125,65.25],[73.5, -3.0625]] | 1    | [[[[1,1],[1,1]]] * 2] |
        | 3       | multiplicative_inverse| 2                                | 1    | [[1] * 3]             |
        | 3       | multiplicative_inverse| 100                              | 1    | [[1] * 3]             |
        | 3       | multiplicative_inverse| -75                              | 1    | [[1] * 3]             |
        | 3       | multiplicative_inverse| -1000                            | 1    | [[1] * 3]             |
        | 3       | multiplicative_inverse| [[35.125,65.25],[73.5, -3.0625]] | 1    | [[[[1,1],[1,1]]] * 3] |


    Scenario Outline: Private Public Subtraction
        Given <players> players
        And secret value <secret>
        And local value <local>
        When player <player> performs private public subtraction on the shared secret
        Then the group should return <result>

        Examples:
        | players | secret  | local       | player | result                                    |
        | 2       | 5       | 1           | 1      | [4] * 2                                   |
        | 3       | 5       | 1.1         | 1      | [3.9] * 3                                 |
        | 4       | 5       | 1.5         | 1      | [3.5] * 4                                 |
        | 3       | [5, 3]  | [1.1, 3.2]  | 1      | [[3.9, -0.2]] * 3                         |




############################################################################################################
## New style scenarios using the calculator service.

    @calculator
    Scenario Outline: Private Add
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players add the shares
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a          | b          | result       |
        | 2       | -2         | -3.5       | -5.5         |
        | 2       | -20        | -30        | -50          |
        | 2       | -200       | -300       | -500         |
        | 2       | -2000      | -3000      | -5000        |
        | 3       | -20000     | -30000     | -50000       |
        | 3       | -200000    | -300000    | -500000      |
        | 3       | -2000000   | -3000000   | -5000000     |
        | 3       | -20000000  | -30000000  | -50000000    |
        | 3       | -200000000 | -300000000 | -500000000   |
        | 3       | -21        | -35        | -56          |
        | 3       | -212       | -351       | -563         |
        | 3       | -2123      | -3512      | -5635        |
        | 3       | -21234     | -35123     | -56357       |
        | 3       | -212345    | -351234    | -563579      |
        | 3       | -2123456   | -3512345   | -5635801     |
        | 3       | -21234567  | -35123458  | -56358025    |
        | 3       | -212345678 | -351234589 | -563580267   |


    @calculator
    Scenario Outline: Private Divide
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players divide the shares
        And the players reveal the result
        Then the result should match <result> to within 3 digits

        Examples:
        | players | a    | b    | result        |
        | 3       | 0    | 5    | 0             |
        | 3       | 1    | 5    | 0.2           |
        | 3       | 2    | 16   | 1/8           |
        | 3       | 37   | 1    | 37.0          |
        | 3       | -1   | 5    | -0.2          |
        | 3       | 2    | -16  | -1/8          |
        | 3       | -37  | 1    | -37.0         |
        | 3       | 0.5  | 0.3  | 1.6666        |


    @calculator
    Scenario Outline: Private Dot Product
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players compute the dot product of the shares
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a          | b       | result |
        | 2       | 5          | 2       | 10     |
        | 2       | [5, 3.5]   | [2, 4]  | 24     |
        | 3       | 5          | -2.5    | -12.5  |
        | 3       | -5         | -2.5    | 12.5   |
        | 3       | [5, 3.5]   | [2, 4]  | 24     |


    @calculator
    Scenario Outline: Private Equality
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players compare the shares for equality
        And the players reveal the binary result
        Then the result should match <result>

        Examples:
        | players  | a                 | b                | result     |
        | 2        | 2                 | 2                | 1          |
        | 2        | 2                 | 3                | 0          |
        | 2        | 2                 | 2.1              | 0          |
        | 2        | 2.1               | 2.1              | 1          |
        | 2        | -2                | -2               | 1          |
        | 2        | -2                | -3               | 0          |
        | 2        | -2                | -2.1             | 0          |
        | 2        | -2.1              | -2.1             | 1          |
        | 2        | -2                | 2                | 0          |
        | 3        | [1, -2, 3, -4.5]  | [1, 2, 3, -4.5]  | [1,0,1,1]  |


    @calculator
    Scenario Outline: Private Floor
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        When the players compute the floor of the share
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a            | result       |
        | 2       | 1            | 1            |
        | 2       | 1.1          | 1            |
        | 2       | -2           | -2           |
        | 2       | -2.1         | -3           |
        | 2       | [1.2, -3.4]  | [1, -4]      |
        | 3       | 1            | 1            |
        | 3       | 1.1          | 1            |
        | 3       | -2           | -2           |
        | 3       | -2.1         | -3           |
        | 3       | [1.2, -3.4]  | [1, -4]      |


    @calculator
    Scenario Outline: Private Less Than
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players compare the shares with less than
        And the players reveal the binary result
        Then the result should match <result>

        Examples:
        | players  | a             | b              | result          |
        | 3        | 0             | 0              | 0               |
        | 3        | 0             | 100            | 1               |
        | 3        | 0             | -100           | 0               |
        | 3        | 0             | 2**-16         | 1               |
        | 3        | 0             | -2**-16        | 0               |
        | 3        | -100          | 100            | 1               |
        | 3        | 100           | 100            | 0               |
        | 3        | -100          | -100           | 0               |
        | 3        | 2**16         | 2**16-1        | 0               |
        | 3        | 2**16-2       | 2**16-1        | 1               |
        | 3        | [[1,2],[3,4]] | [[2,2],[4,4]]  | [[1,0],[1,0]]   |


    @calculator
    Scenario Outline: Private Logical And
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares binary <a>
        And player 1 secret shares binary <b>
        When the players compute the logical and of the shares
        And the players reveal the binary result
        Then the result should match <result>

        Examples:
        | players  | a | b | result |
        | 3        | 0 | 0 | 0      |
        | 3        | 0 | 1 | 0      |
        | 3        | 1 | 0 | 0      |
        | 3        | 1 | 1 | 1      |


    @calculator
    Scenario Outline: Private Logical Exclusive Or
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares binary <a>
        And player 1 secret shares binary <b>
        When the players compute the logical exclusive or of the shares
        And the players reveal the binary result
        Then the result should match <result>

        Examples:
        | players | a | b | result |
        | 3       | 0 | 0 | 0      |
        | 3       | 0 | 1 | 1      |
        | 3       | 1 | 0 | 1      |
        | 3       | 1 | 1 | 0      |


    @calculator
    Scenario Outline: Private Logical Or
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares binary <a>
        And player 1 secret shares binary <b>
        When the players compute the logical or of the shares
        And the players reveal the binary result
        Then the result should match <result>

        Examples:
        | players | a | b | result |
        | 2       | 0 | 0 | 0      |
        | 2       | 0 | 1 | 1      |
        | 2       | 1 | 0 | 1      |
        | 2       | 1 | 1 | 1      |


    @calculator
    Scenario Outline: Private Max
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players compute the maximum of the shares
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a              | b                | result           |
        | 3       | 2              | 3.5              | 3.5              |
        | 3       | 3.5            | 2                | 3.5              |
        | 3       | -3             | 2                | 2                |
        | 3       | 2              | -3               | 2                |
        | 3       | -4             | -3               | -3               |
        | 3       | [2, 3, -2, -1] | [3.5, 1, 1, -4]  | [3.5, 3, 1, -1]  |


    @calculator
    Scenario Outline: Private Min
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players compute the minimum of the shares
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a              | b                  | result           |
        | 3       | 2              | 3.5                | 2                |
        | 3       | 3.5            | 2                  | 2                |
        | 3       | -3             | 2                  | -3               |
        | 3       | 2              | -3                 | -3               |
        | 3       | -4             | -3                 | -4               |
        | 3       | [2, 3, -2, -1] | [3.5, 1, -2, -4]   | [2, 1, -2, -4]   |


    @calculator
    Scenario Outline: Private Multiply
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players multiply the shares
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a          | b       | result        |
        | 2       | 5          | 2       | 10            |
        | 2       | 5          | 2.5     | 12.5          |
        | 2       | 5          | -2.5    | -12.5         |
        | 2       | -5         | -2.5    | 12.5          |
        | 2       | [5, 3.5]   | [2, 4]  | [10, 14]      |
        | 3       | 5          | 2       | 10            |
        | 3       | 5          | 2.5     | 12.5          |
        | 3       | 5          | -2.5    | -12.5         |
        | 3       | -5         | -2.5    | 12.5          |
        | 3       | [5, 3.5]   | [2, 4]  | [10, 14]      |
        | 4       | 5          | 2       | 10            |
        | 4       | 5          | 2.5     | 12.5          |
        | 4       | 5          | -2.5    | -12.5         |
        | 4       | -5         | -2.5    | 12.5          |
        | 4       | [5, 3.5]   | [2, 4]  | [10, 14]      |
        | 5       | 5          | 2       | 10            |
        | 5       | 5          | 2.5     | 12.5          |
        | 5       | 5          | -2.5    | -12.5         |
        | 5       | -5         | -2.5    | 12.5          |
        | 5       | [5, 3.5]   | [2, 4]  | [10, 14]      |


    @calculator
    Scenario Outline: Private Public Power
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        And unencoded public value <b>
        When the players raise the share to a public power
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a    | b    | result   |
        | 3       | 0    | 5    | 0        |
        | 3       | 1    | 5    | 1        |
        | 3       | 2    | 16   | 65536    |
        | 3       | -1   | 4    | 1        |
        | 3       | -2   | 16   | 65536    |
        | 3       | -1   | 5    | -1       |

        Examples:
        | players | a                      | b  | result                                |
        | 3       | [-1, 2, 3.75, -2.0625] | 3  | [-1, 8, 52.734375, -8.773681640625]   |


    @calculator
    Scenario Outline: Private ReLU
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        When the players compute the relu of the share
        And the players reveal the result
        Then the result should match <result> to within 4 digits

        Examples:
        | players | a                       | result                  |
        | 2       | 1                       | 1                       |
        | 2       | 1.1                     | 1.1                     |
        | 2       | -2                      | 0                       |
        | 2       | -2.1                    | 0                       |
        | 2       | [[0, 3.4],[-1234,1234]] | [[0,3.4],[0,1234]]      |
        | 3       | 1                       | 1                       |
        | 3       | 1.1                     | 1.1                     |
        | 3       | -2                      | 0                       |
        | 3       | -2.1                    | 0                       |
        | 3       | [[0, 3.4],[-1234,1234]] | [[0,3.4],[0,1234]]      |


    @calculator
    Scenario Outline: Private Sum
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        When the players compute the sum of the share
        And the players reveal the result
        Then the result should match <result> to within 4 digits

        Examples:
        | players | a             | result |
        | 2       | 1             | 1      |
        | 2       | [1.2, -3.4]   | -2.2   |
        | 3       | 1.1           | 1.1    |
        | 3       | [1.2, -3.4]   | -2.2   |


    @calculator
    Scenario Outline: Private Zigmoid
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And player 0 secret shares <a>
        When the players compute the zigmoid of the share
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a                        | result                  |
        | 2       | 1                        | 1                       |
        | 2       | 1.1                      | 1                       |
        | 2       | -2                       | 0                       |
        | 2       | -2.1                     | 0                       |
        | 2       | 0.25                     | .75                     |
        | 2       | 0.75                     | 1                       |
        | 2       | -.0625                   | .4375                   |
        | 2       | -.5                      | 0                       |
        | 2       | [[0, 3.4],[-1234, 1234]] | [[0.5, 1],[0, 1]]       |
        | 3       | 1                        | 1                       |
        | 3       | 1.1                      | 1                       |
        | 3       | -2                       | 0                       |
        | 3       | -2.1                     | 0                       |
        | 3       | 0.25                     | .75                     |
        | 3       | 0.75                     | 1                       |
        | 3       | -.0625                   | .4375                   |
        | 3       | -.5                      | 0                       |
        | 3       | [[0, 3.4],[-1234, 1234]] | [[0.5, 1],[0, 1]]       |


    @calculator
    Scenario Outline: Public Private Add
        Given a calculator service with <players> players
        And an AdditiveProtocol object
        And public value <a>
        And player 1 secret shares <b>
        When the players add the public value and the share
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a          | b          | result      |
        | 2       | -2         | -3.5       | -5.5        |
        | 2       | -20        | -30        | -50         |
        | 2       | -200       | -300       | -500        |
        | 2       | -2000      | -3000      | -5000       |
        | 3       | -20000     | -30000     | -50000      |
        | 3       | -200000    | -300000    | -500000     |
        | 3       | -2000000   | -3000000   | -5000000    |
        | 3       | -20000000  | -30000000  | -50000000   |
        | 3       | -200000000 | -300000000 | -500000000  |
        | 3       | -21        | -35        | -56         |
        | 3       | -212       | -351       | -563        |
        | 3       | -2123      | -3512      | -5635       |
        | 3       | -21234     | -35123     | -56357      |
        | 3       | -212345    | -351234    | -563579     |
        | 3       | -2123456   | -3512345   | -5635801    |
        | 3       | -21234567  | -35123458  | -56358025   |
        | 3       | -212345678 | -351234589 | -563580267  |


