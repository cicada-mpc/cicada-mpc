Feature: Shamir Protocol

    Scenario Outline: Random Round Trip Shamir Sharing
        Given <players> players
        When player <player> shamir shares and reveals random secrets, the revealed secrets should match the originals

        Examples:
        | players | player |
        | 3       | 0      |
        | 4       | 0      |
        | 5       | 0      |


############################################################################################################
## New style scenarios using the calculator service.


    @calculator
	Scenario: Inter Protocol Share Repetition
        Given a calculator service with 3 players
        And a ShamirProtocol object
        And player 1 secret shares 5
        And the players extract the share storage
        And a ShamirProtocol object
        And player 1 secret shares 5
        And the players extract the share storage
        Then the two values should not be equal


    @calculator
	Scenario: Intra Protocol Share Repetition
        Given a calculator service with 3 players
        And a ShamirProtocol object
        And player 1 secret shares 5
        And the players extract the share storage
        And player 1 secret shares 5
        And the players extract the share storage
        Then the two values should not be equal


    @calculator
    Scenario Outline: Private Add
        Given a calculator service with <players> players
        And a ShamirProtocol object
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players add the shares
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a          | b          | result       |
        | 3       | -2         | -3.5       | -5.5         |
        | 3       | -20        | -30        | -50          |
        | 3       | -200       | -300       | -500         |
        | 3       | -2000      | -3000      | -5000        |
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
        And a ShamirProtocol object
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
    Scenario Outline: Private Equality
        Given a calculator service with <players> players
        And a ShamirProtocol object
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players compare the shares for equality
        And the players reveal the result without decoding
        Then the result should match <result>

        Examples:
        | players  | a                 | b                | result     |
        | 3        | 2                 | 2                | 1          |
        | 3        | 2                 | 3                | 0          |
        | 3        | 2                 | 2.1              | 0          |
        | 3        | 2.1               | 2.1              | 1          |
        | 3        | -2                | -2               | 1          |
        | 3        | -2                | -3               | 0          |
        | 3        | -2                | -2.1             | 0          |
        | 3        | -2.1              | -2.1             | 1          |
        | 3        | -2                | 2                | 0          |
        | 3        | [1, -2, 3, -4.5]  | [1, 2, 3, -4.5]  | [1,0,1,1]  |


    @calculator
    Scenario Outline: Private Floor
        Given a calculator service with <players> players
        And a ShamirProtocol object
        And player 0 secret shares <a>
        When the players compute the floor of the share
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a            | result       |
        | 4       | 1            | 1            |
        | 4       | 1.1          | 1            |
        | 4       | -2           | -2           |
        | 4       | -2.1         | -3           |
        | 4       | [1.2, -3.4]  | [1, -4]      |
        | 3       | 1            | 1            |
        | 3       | 1.1          | 1            |
        | 3       | -2           | -2           |
        | 3       | -2.1         | -3           |
        | 3       | [1.2, -3.4]  | [1, -4]      |


    @calculator
    Scenario Outline: Private Less Than
        Given a calculator service with <players> players
        And a ShamirProtocol object
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players compare the shares with less than
        And the players reveal the result without decoding
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
        And a ShamirProtocol object
        And player 0 secret shares <a> without encoding
        And player 1 secret shares <b> without encoding
        When the players compute the logical and of the shares
        And the players reveal the result without decoding
        Then the result should match <result>

        Examples:
        | players  | a | b | result |
        | 3        | 0 | 0 | [0]    |
        | 3        | 0 | 1 | [0]    |
        | 3        | 1 | 0 | [0]    |
        | 3        | 1 | 1 | [1]    |


    @calculator
    Scenario Outline: Private Logical Exclusive Or
        Given a calculator service with <players> players
        And a ShamirProtocol object
        And player 0 secret shares <a> without encoding
        And player 1 secret shares <b> without encoding
        When the players compute the logical exclusive or of the shares
        And the players reveal the result without decoding
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
        And a ShamirProtocol object
        And player 0 secret shares <a> without encoding
        And player 1 secret shares <b> without encoding
        When the players compute the logical or of the shares
        And the players reveal the result without decoding
        Then the result should match <result>

        Examples:
        | players | a | b | result |
        | 3       | 0 | 0 | 0      |
        | 3       | 0 | 1 | 1      |
        | 3       | 1 | 0 | 1      |
        | 3       | 1 | 1 | 1      |


    @calculator
    Scenario Outline: Private Max
        Given a calculator service with <players> players
        And a ShamirProtocol object
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
        And a ShamirProtocol object
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
        And a ShamirProtocol object
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players multiply the shares
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a          | b       | result        |
        | 5       | 5          | 2       | 10            |
        | 5       | 5          | 2.5     | 12.5          |
        | 5       | 5          | -2.5    | -12.5         |
        | 5       | -5         | -2.5    | 12.5          |
        | 5       | [5, 3.5]   | [2, 4]  | [10, 14]      |
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
    Scenario Outline: Private Multiplicative Inverse
        Given a calculator service with <players> players
        And a ShamirProtocol object
        And player 0 secret shares <a>
        When the players compute the multiplicative inverse
        And the players multiply the shares without truncation
        And the players reveal the result without decoding
        Then the result should match <result>

        Examples:
        | players | a                                | result        |
        | 4       | 2                                | 1             |
        | 4       | 100                              | 1             |
        | 4       | -75                              | 1             |
        | 4       | -1000                            | 1             |
        | 4       | [[35.125,65.25],[73.5, -3.0625]] | [[1,1],[1,1]] |
        | 3       | 2                                | 1             |
        | 3       | 100                              | 1             |
        | 3       | -75                              | 1             |
        | 3       | -1000                            | 1             |
        | 3       | [[35.125,65.25],[73.5, -3.0625]] | [[1,1],[1,1]] |


    @calculator
    Scenario Outline: Private Public Power
        Given a calculator service with <players> players
        And a ShamirProtocol object
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
    Scenario Outline: Private Public Subtract
        Given a calculator service with <players> players
        And a ShamirProtocol object
        And player 0 secret shares <a>
        And public value <b>
        When the players subtract the public value from the share
        And the players reveal the result
        Then the result should match <result> to within 4 digits

        Examples:
        | players | a       | b          | result       |
        | 3       | 5       | 1          | 4            |
        | 3       | 5       | 1.1        | 3.9          |
        | 4       | 5       | 1.5        | 3.5          |
        | 3       | [5, 3]  | [1.1, 3.2] | [3.9, -0.2]  |


    @calculator
    Scenario Outline: Private ReLU
        Given a calculator service with <players> players
        And a ShamirProtocol object
        And player 0 secret shares <a>
        When the players compute the relu of the share
        And the players reveal the result
        Then the result should match <result> to within 4 digits

        Examples:
        | players | a                       | result                  |
        | 4       | 1                       | 1                       |
        | 4       | 1.1                     | 1.1                     |
        | 4       | -2                      | 0                       |
        | 4       | -2.1                    | 0                       |
        | 4       | [[0, 3.4],[-1234,1234]] | [[0,3.4],[0,1234]]      |
        | 3       | 1                       | 1                       |
        | 3       | 1.1                     | 1.1                     |
        | 3       | -2                      | 0                       |
        | 3       | -2.1                    | 0                       |
        | 3       | [[0, 3.4],[-1234,1234]] | [[0,3.4],[0,1234]]      |


    @calculator
    Scenario Outline: Private Zigmoid
        Given a calculator service with <players> players
        And a ShamirProtocol object
        And player 0 secret shares <a>
        When the players compute the zigmoid of the share
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a                        | result                  |
        | 4       | 1                        | 1                       |
        | 4       | 1.1                      | 1                       |
        | 4       | -2                       | 0                       |
        | 4       | -2.1                     | 0                       |
        | 4       | 0.25                     | .75                     |
        | 4       | 0.75                     | 1                       |
        | 4       | -.0625                   | .4375                   |
        | 4       | -.5                      | 0                       |
        | 4       | [[0, 3.4],[-1234, 1234]] | [[0.5, 1],[0, 1]]       |
        | 3       | 1                        | 1                       |
        | 3       | 1.1                      | 1                       |
        | 3       | -2                       | 0                       |
        | 3       | -2.1                     | 0                       |
        | 3       | 0.25                     | .75                     |
        | 3       | 0.75                     | 1                       |
        | 3       | -.0625                   | .4375                   |


    @calculator
    Scenario Outline: Public Private Addition
        Given a calculator service with <players> players
        And a ShamirProtocol object
        And public value <a>
        And player 1 secret shares <b>
        When the players add the public value and the share
        And the players reveal the result
        Then the result should match <result>

        Examples:
        | players | a          | b          | result      |
        | 3       | -2         | -3.5       | -5.5        |
        | 3       | -20        | -30        | -50         |
        | 3       | -200       | -300       | -500        |
        | 3       | -2000      | -3000      | -5000       |
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


    @calculator
    Scenario Outline: Random Bitwise Secret
        Given a calculator service with <players> players
        And a ShamirProtocol object
        When the players generate <bits> random bits with seed <seed>
        And the players reveal the result without decoding
        And the players swap
        And the players reveal the result without decoding
        And the players swap
        Then the value of the bits in big-endian order should match the random value.

        Examples:
        | players | bits  | seed |
        | 3       | 1     | 1234 |
        | 3       | 2     | 1235 |
        | 3       | 4     | 1236 |
        | 3       | 8     | 1237 |
        | 3       | 8     | 1238 |
        | 3       | 8     | 1239 |


    @calculator
    Scenario Outline: Startup Reliability
        Given a calculator service with <players> players
        Then <count> ShamirProtocol objects can be created without error

        Examples:
        | players | count |
        | 3       | 10    |
        | 4       | 10    |
        | 10      | 10    |
