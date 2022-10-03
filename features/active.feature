Feature: Active Protocol


    @calculator
	Scenario: Inter Protocol Share Repetition
        Given a calculator service with 3 players
        And a new Active protocol suite
        And player 1 secret shares 5
        And the players extract the share storage
        And a new Active protocol suite
        And player 1 secret shares 5
        And the players extract the share storage
        Then the two values should not be equal


    @calculator
	Scenario: Intra Protocol Share Repetition
        Given a calculator service with 3 players
        And a new Active protocol suite
        And player 1 secret shares 5
        And the players extract the share storage
        And player 1 secret shares 5
        And the players extract the share storage
        Then the two values should not be equal


    @calculator
    Scenario Outline: Active Verification
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        When the players verify the share
        Then the result should match <result>

        Examples:
        | players | a              | result       |
        | 3       | 42             | True         |
        | 3       | [1, 2.5, -3.1] | True         |


    @calculator
    Scenario Outline: Active Verification With Additive Tampering
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        And player 1 tampers with the additive portion of its ActiveArrayShare
        When the players verify the share
        Then the result should match <result>

        Examples:
        | players | a              | result        |
        | 3       | 42             | False         |
        | 3       | [1, 2.5, -3.1] | False         |


    @calculator
    Scenario Outline: Active Verification With Shamir Tampering
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        And player 1 tampers with the Shamir portion of its ActiveArrayShare
        When the players verify the share
        Then the result should match <result>

        Examples:
        | players | a              | result        |
        | 3       | 42             | False         |
        | 3       | [1, 2.5, -3.1] | False         |


    @calculator
    Scenario Outline: Private Absolute
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        When the players compute the absolute value of the share
        And the players reveal the secret
        Then the result should match <result> to within 4 digits

        Examples:
        | players | a     | result        |
        | 3       | 0     | 0             |
        | 3       | 0.5   | 0.5           |
        | 3       | 1     | 1             |
        | 3       | 37.3  | 37.3          |
        | 3       | -1    | 1             |
        | 3       | -37.3 | 37.3          |


    @calculator
    Scenario Outline: Private Add
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players add the shares
        And the players reveal the secret
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
    Scenario Outline:Private Additive Inverse
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player <player> secret shares <value>
        When the players compute the additive inverse
        And the players reveal the secret
        Then the results should match <result> to within 4 digits

        @wip
        Examples:
        | players | player | value         | result      |
        | 3       | 0      | 1             | -1          |
        | 3       | 1      | 2.56          | -2.56       |
        | 3       | 2      | -3.5          | 3.5         |
        | 3       | 2      | [2.3, 7.9]    | [-2.3, -7.9]|


    @calculator
    Scenario Outline: Private Bit Compose 
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        When the players compute the composition of the shared bits
        And the players reveal the secret
        Then the result should match <result> to within 4 digits

        Examples:
        | players | a         | result        |
        | 3       | [0,1,0,1] | 5             |
        | 3       | [0,0,0,0] | 0             |
        | 3       | [1,1,1,1] | 15            |
        | 3       | [1,0,1,0] | 10            |
        | 3       | [1,1,0,0] | 12            |
        | 3       | [0,0,1,1] | 3             |


    @calculator
    Scenario Outline: Private Bit Decompose 
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        When the players compute the decomposition of the shared secrets
        And the players reveal the secret bits
        Then the result should match <result> to within 4 digits

        Examples:
        | players | a         | result                   |
        | 3       |  5        |  [0]*44+[0,1,0,1]+[0]*16 |
        | 3       |  0        |  [0]*44+[0,0,0,0]+[0]*16 |
        | 3       |  15       |  [0]*44+[1,1,1,1]+[0]*16 |
        | 3       |  10       |  [0]*44+[1,0,1,0]+[0]*16 |
        | 3       |  12       |  [0]*44+[1,1,0,0]+[0]*16 |
        | 3       |  3        |  [0]*44+[0,0,1,1]+[0]*16 |


    @calculator
    Scenario Outline: Private Divide
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players divide the shares
        And the players reveal the secret
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

        @wip
        Examples:
        | players | a    | b    | result        |
        | 3       | 0.5  | 3  | .16666        |


    @calculator
    Scenario Outline: Private Dot Product
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players compute the dot product of the shares
        And the players reveal the secret
        Then the result should match <result>

        Examples:
        | players | a          | b       | result |
        | 3       | 5          | 2       | 10     |
        | 3       | [5, 3.5]   | [2, 4]  | 24     |
        | 3       | 5          | -2.5    | -12.5  |
        | 3       | -5         | -2.5    | 12.5   |
        | 3       | [5, 3.5]   | [2, 4]  | 24     |


    @calculator
    Scenario Outline: Private Equality
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players compare the shares for equality
        And the players reveal the secret bits
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
        And a new Active protocol suite
        And player 0 secret shares <a>
        When the players compute the floor of the share
        And the players reveal the secret
        Then the result should match <result>

        Examples:
        | players | a            | result       |
        | 3       | 1            | 1            |
        | 3       | 1.1          | 1            |
        | 3       | -2           | -2           |
        | 3       | -2.1         | -3           |
        | 3       | [1.2, -3.4]  | [1, -4]      |


    @calculator
    Scenario Outline: Private Less Than
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players compare the shares with less than
        And the players reveal the secret bits
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
    Scenario Outline: Private Less Than Zero
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        When the players compare the shares with less than zero
        And the players reveal the secret bits
        Then the result should match <result>

        Examples:
        | players  | a                 | result          |
        | 3        | 0                 | 0               |
        | 3        | 100               | 0               |
        | 3        | -100              | 1               |
        | 3        | 2**-16            | 0               |
        | 3        | -2**-16           | 1               |
        | 3        | [[0,100],[-3,4]]  | [[0,0],[1,0]]   |


    @calculator
    Scenario Outline: Private Logical And
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares the bits <a>
        And player 1 secret shares the bits <b>
        When the players compute the logical and of the shares
        And the players reveal the secret bits
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
        And a new Active protocol suite
        And player 0 secret shares the bits <a>
        And player 1 secret shares the bits <b>
        When the players compute the logical exclusive or of the shares
        And the players reveal the secret bits
        Then the result should match <result>

        Examples:
        | players | a | b | result |
        | 3       | 0 | 0 | 0      |
        | 3       | 0 | 1 | 1      |
        | 3       | 1 | 0 | 1      |
        | 3       | 1 | 1 | 0      |


    @calculator
    Scenario Outline: Private Logical Not
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares the bits <a>
        When the players compute the logical not of the share
        And the players reveal the secret bits
        Then the result should match <result>

        Examples:
        | players | a | result |
        | 3       | 0 | 1      |
        | 3       | 1 | 0      |


    @calculator
    Scenario Outline: Private Logical Or
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares the bits <a>
        And player 1 secret shares the bits <b>
        When the players compute the logical or of the shares
        And the players reveal the secret bits
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
        And a new Active protocol suite
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players compute the maximum of the shares
        And the players reveal the secret
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
        And a new Active protocol suite
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players compute the minimum of the shares
        And the players reveal the secret
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
        And a new Active protocol suite
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players multiply the shares
        And the players reveal the secret
        Then the result should match <result>

        Examples:
        | players | a          | b       | result        |
        | 3       | 5          | 2       | 10            |
        | 3       | 5          | 2.5     | 12.5          |
        | 3       | 5          | -2.5    | -12.5         |
        | 3       | -5         | -2.5    | 12.5          |
        | 3       | [5, 3.5]   | [2, 4]  | [10, 14]      |


    @calculator
    Scenario Outline: Private Multiplicative Inverse
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        When the players compute the multiplicative inverse
        And the players multiply the shares without truncation
        And the players reveal the field values
        Then the result should match <result>

        Examples:
        | players | a                                | result        |
        | 3       | 2                                | 1             |
        | 3       | 100                              | 1             |
        | 3       | -75                              | 1             |
        | 3       | -1000                            | 1             |
        | 3       | [[35.125,65.25],[73.5, -3.0625]] | [[1,1],[1,1]] |


    @calculator
    Scenario Outline: Private Public Power
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        And public value <b>
        When the players raise the share to the public power
        And the players reveal the secret
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
    Scenario Outline: Private Public Power Field
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        And public value <b>
        When the players raise the share to the public power in the field
        And the players reveal the field values
        Then the result should match <result>

        Examples:
        | players | a    | b        | result   |
        | 3       | 0    | 2**64-60 | 0        |
        | 3       | 1    | 2**64-60 | 1        |
        | 3       | 2    | 2**64-60 | 1        |
        | 3       | -1   | 2**64-60 | 1        |
        | 3       | -2   | 2**64-60 | 1        |
        | 3       | -1   | 2**64-60 | 1        |

        Examples:
        | players | a                      | b        | result      |
        | 3       | [-1, 2, 3.75, -2.0625] | 2**64-60 | [1,1,1,1]   |


    @calculator
    Scenario Outline: Private ReLU
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        When the players compute the relu of the share
        And the players reveal the secret
        Then the result should match <result> to within 4 digits

        Examples:
        | players | a                       | result                  |
        | 3       | 1                       | 1                       |
        | 3       | 1.1                     | 1.1                     |
        | 3       | -2                      | 0                       |
        | 3       | -2.1                    | 0                       |
        | 3       | [[0, 3.4],[-1234,1234]] | [[0,3.4],[0,1234]]      |


    @calculator
    Scenario Outline: Private Subtract
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        And player 1 secret shares <b>
        When the players subtract the shares
        And the players reveal the secret
        Then the result should match <result> to within 4 digits

        Examples:
        | players | a       | b           | result        |
        | 3       | 5       | 1           | 4             |
        | 3       | 5       | 1.1         | 3.9           |
        | 3       | 5       | 1.5         | 3.5           |
        | 3       | [5, 3]  | [1.1, 3.2]  | [3.9, -0.2]   |


    @calculator
    Scenario Outline: Private Sum
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        When the players compute the sum of the share
        And the players reveal the secret
        Then the result should match <result> to within 4 digits

        Examples:
        | players | a             | result |
        | 3       | 1             | 1      |
        | 3       | 1.1           | 1.1    |
        | 3       | [1.2, -3.4]   | -2.2   |


    @calculator
    Scenario Outline: Private Uniform
        Given a calculator service with <players> players
        And a new Active protocol suite
        When the players generate a private uniform array with shape <shape>
        And the players reveal the secret
        Then the results should match shape <shape>

        Examples:
        | players | shape  |
        | 3       | ()     |
        | 3       | (1,)   |
        | 3       | (2, 2) |


    @calculator
    Scenario Outline: Private Zigmoid
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player 0 secret shares <a>
        When the players compute the zigmoid of the share
        And the players reveal the secret
        Then the result should match <result>

        Examples:
        | players | a                        | result                  |
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
    Scenario Outline: Random Bitwise Secret
        Given a calculator service with <players> players
        And a new Active protocol suite
        When the players generate <bits> random bits
        And the players reveal the field values
        And the players swap
        And the players reveal the secret bits
        And the players swap
        Then the value of the bits in big-endian order should match the random value.

        Examples:
        | players | bits  |
        | 3       | 1     |
        | 3       | 2     |
        | 3       | 4     |
        | 3       | 8     |
        | 4       | 1     |
        | 4       | 2     |
        | 4       | 4     |
        | 4       | 8     |


    @calculator
    Scenario Outline: Resharing
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player <player> secret shares <value>
        And the players reshare the secret
        When the players reveal the secret
        Then the results should match <result> to within 4 digits

        Examples:
        | players | player | value         | result      |
        | 3       | 0      | 1             | 1           |
        | 3       | 1      | 2.56          | 2.56        |
        | 3       | 2      | -3.5          | -3.5        |
        | 3       | 2      | [2.3, 7.9]    | [2.3, 7.9]  |


    @calculator
    Scenario Outline: Round Trip Sharing
        Given a calculator service with <players> players
        And a new Active protocol suite
        And player <player> secret shares <value>
        When the players reveal the secret
        Then the result should match <value> to within 4 digits

        Examples:
        | players | player | value         |
        | 3       | 0      | 1             |
        | 3       | 1      | 2.56          |
        | 3       | 2      | -3.5          |
        | 3       | 2      | [2.3, 7.9]    |


    @calculator
    Scenario Outline: Startup Reliability
        Given a calculator service with <players> players
        Then <count> Active protocol objects can be created without error

        Examples:
        | players | count |
        | 3       | 10    |
        | 10      | 10    |

