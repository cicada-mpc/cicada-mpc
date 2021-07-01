Feature: Additive Protocol

    Scenario: Inter-session Repetition
        Given 3 players
        When secret sharing the same value for 10 sessions
	    Then the shares should never be repeated


	Scenario: Intra-session Repetition
        Given 3 players
        When secret sharing the same value 10 times in one session
        Then the shares should never be repeated


    Scenario Outline: Secret Input
        Given <players> players
        When player <player> receives secret input <input>
        Then the group should return <result>

        Examples:
        | players |  player | input     | result            |
        | 1       |  0      | "1.2"     | [1.2] * 1         |
        | 2       |  0      | "1.2"     | [1.2] * 2         |
        | 2       |  1      | "1.2"     | [1.2] * 2         |
        | 3       |  1      | "-5"      | [-5] * 3          |
        | 4       |  2      | "-13.7"   | [-13.7] * 4       |


    Scenario Outline: Random Round Trip Sharing
        Given <players> players
        When player <player> shares and reveals <count> random secrets, the revealed secrets should match the originals

        Examples:
        | players | player | count      |
        | 2       | 0      | 100       |
        | 3       | 1      | 100        |
        | 4       | 2      | 100        |


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


    Scenario Outline: Addition
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation               | a  | b    | count | result              |
        | 2       | public-private addition | 2  | 3    | 10    | [[5] * 2] * 10        |
        | 2       | public-private addition | 2  | 3.5  | 10    | [[5.5] * 2] * 10     |
        | 2       | public-private addition | 2  | -3.5 | 10    | [[-1.5] * 2] * 10   |
        | 2       | public-private addition | -2 | -3.5 | 10    | [[-5.5] * 2] * 10   |
        | 3       | public-private addition | -2 | -3.5 | 10    | [[-5.5] * 3] * 10   |
        | 3       | public-private addition | -20 | -30 | 10    | [[-50] * 3] * 10   |
        | 3       | public-private addition | -200 | -300 | 10    | [[-500] * 3] * 10   |
        | 3       | public-private addition | -2000 | -3000 | 10    | [[-5000] * 3] * 10   |
        | 3       | public-private addition | -20000 | -30000 | 10    | [[-50000] * 3] * 10   |
        | 3       | public-private addition | -200000 | -300000 | 10    | [[-500000] * 3] * 10   |
        | 3       | public-private addition | -2000000 | -3000000 | 10    | [[-5000000] * 3] * 10   |
        | 3       | public-private addition | -20000000 | -30000000 | 10    | [[-50000000] * 3] * 10   |
        | 3       | public-private addition | -200000000 | -300000000 | 10    | [[-500000000] * 3] * 10   |
        | 3       | public-private addition | -21 | -35 | 10    | [[-56] * 3] * 10   |
        | 3       | public-private addition | -212 | -351 | 10    | [[-563] * 3] * 10   |
        | 3       | public-private addition | -2123 | -3512 | 10    | [[-5635] * 3] * 10   |
        | 3       | public-private addition | -21234 | -35123 | 10    | [[-56357] * 3] * 10   |
        | 3       | public-private addition | -212345 | -351234 | 10    | [[-563579] * 3] * 10   |
        | 3       | public-private addition | -2123456 | -3512345 | 10    | [[-5635801] * 3] * 10   |
        | 3       | public-private addition | -21234567 | -35123458 | 10    | [[-56358025] * 3] * 10   |
        | 3       | public-private addition | -212345678 | -351234589 | 10    | [[-563580267] * 3] * 10   |

        | 2       | private-private addition | 2  | 3    | 10    | [[5] * 2] * 10         |
        | 2       | private-private addition | 2  | 3.5  | 10    | [[5.5] * 2] * 10     |
        | 2       | private-private addition | 2  | -3.5 | 10    | [[-1.5] * 2] * 10   |
        | 2       | private-private addition | -2 | -3.5 | 10    | [[-5.5] * 2] * 10   |
        | 3       | private-private addition | -2 | -3.5 | 10    | [[-5.5] * 3] * 10   |
        | 3       | private-private addition | -20 | -30 | 10    | [[-50] * 3] * 10   |
        | 3       | private-private addition | -200 | -300 | 10    | [[-500] * 3] * 10   |
        | 3       | private-private addition | -2000 | -3000 | 10    | [[-5000] * 3] * 10   |
        | 3       | private-private addition | -20000 | -30000 | 10    | [[-50000] * 3] * 10   |
        | 3       | private-private addition | -200000 | -300000 | 10    | [[-500000] * 3] * 10   |
        | 3       | private-private addition | -2000000 | -3000000 | 10    | [[-5000000] * 3] * 10   |
        | 3       | private-private addition | -20000000 | -30000000 | 10    | [[-50000000] * 3] * 10   |
        | 3       | private-private addition | -200000000 | -300000000 | 10    | [[-500000000] * 3] * 10   |
        | 3       | private-private addition | -21 | -35 | 10    | [[-56] * 3] * 10   |
        | 3       | private-private addition | -212 | -351 | 10    | [[-563] * 3] * 10   |
        | 3       | private-private addition | -2123 | -3512 | 10    | [[-5635] * 3] * 10   |
        | 3       | private-private addition | -21234 | -35123 | 10    | [[-56357] * 3] * 10   |
        | 3       | private-private addition | -212345 | -351234 | 10    | [[-563579] * 3] * 10   |
        | 3       | private-private addition | -2123456 | -3512345 | 10    | [[-5635801] * 3] * 10   |
        | 3       | private-private addition | -21234567 | -35123458 | 10    | [[-56358025] * 3] * 10   |
        | 3       | private-private addition | -212345678 | -351234589 | 10    | [[-563580267] * 3] * 10   |

    Scenario Outline: Untruncated Multiplication
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation                                  | a   | b    | count | result                |
        | 2       | private-private untruncated multiplication | 5   | 2    | 10    | [[655360] * 2] * 10       |
        | 2       | private-private untruncated multiplication | 5   | 2.5  | 10    | [[819200] * 2] * 10     |
        | 2       | private-private untruncated multiplication | 5   | -2.5 | 10    | [[-819200] * 2] * 10    |
        | 2       | private-private untruncated multiplication | -5  | -2.5 | 10    | [[819200] * 2] * 10     |
        | 2       | private-private untruncated multiplication | [5, 3.5] | [2, 4]  | 10    | [[[655360, 917504]] * 2] * 10       |
        | 3       | private-private untruncated multiplication | 5   | 2    | 10    | [[655360] * 3] * 10       |
        | 3       | private-private untruncated multiplication | 5   | 2.5  | 10    | [[819200] * 3] * 10     |
        | 3       | private-private untruncated multiplication | 5   | -2.5 | 10    | [[-819200] * 3] * 10    |
        | 3       | private-private untruncated multiplication | -5  | -2.5 | 10    | [[819200] * 3] * 10     |
        | 3       | private-private untruncated multiplication | [5, 3.5] | [2, 4]  | 10    | [[[655360, 917504]] * 3] * 10       |
        | 4       | private-private untruncated multiplication | 5   | 2    | 10    | [[655360] * 4] * 10       |
        | 4       | private-private untruncated multiplication | 5   | 2.5  | 10    | [[819200] * 4] * 10     |
        | 4       | private-private untruncated multiplication | 5   | -2.5 | 10    | [[-819200] * 4] * 10    |
        | 4       | private-private untruncated multiplication | -5  | -2.5 | 10    | [[819200] * 4] * 10     |
        | 4       | private-private untruncated multiplication | [5, 3.5] | [2, 4]  | 10    | [[[655360, 917504]] * 4] * 10       |
        | 5       | private-private untruncated multiplication | 5   | 2    | 10    | [[655360] * 5] * 10       |
        | 5       | private-private untruncated multiplication | 5   | 2.5  | 10    | [[819200] * 5] * 10     |
        | 5       | private-private untruncated multiplication | 5   | -2.5 | 10    | [[-819200] * 5] * 10    |
        | 5       | private-private untruncated multiplication | -5  | -2.5 | 10    | [[819200] * 5] * 10     |
        | 5       | private-private untruncated multiplication | [5, 3.5] | [2, 4]  | 10    | [[[655360, 917504]] * 5] * 10       |


    Scenario Outline: Logical Exclusive Or
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation           | a      | b      | count | result             |
        | 2       | private-private xor | 0      | 0      | 10    | [[0] * 2] * 10     |
        | 2       | private-private xor | 0      | 1      | 10    | [[1] * 2] * 10     |
        | 2       | private-private xor | 1      | 0      | 10    | [[1] * 2] * 10     |
        | 2       | private-private xor | 1      | 1      | 10    | [[0] * 2] * 10     |


    Scenario Outline: Logical Or
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation          | a      | b      | count | result             |
        | 2       | private-private or | 0      | 0      | 10    | [[0] * 2] * 10     |
        | 2       | private-private or | 0      | 1      | 10    | [[1] * 2] * 10     |
        | 2       | private-private or | 1      | 0      | 10    | [[1] * 2] * 10     |
        | 2       | private-private or | 1      | 1      | 10    | [[1] * 2] * 10     |


    Scenario Outline: Max
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation          | a      | b      | count | result            |
        | 3       | max                | 2      | 3.5    | 10    | [[3.5] * 3] * 10  |
        | 3       | max                | 3.5    | 2      | 10    | [[3.5] * 3] * 10  |
        | 3       | max                | -3     | 2      | 10    | [[2] * 3] * 10    |
        | 3       | max                | 2      | -3     | 10    | [[2] * 3] * 10    |
        | 3       | max                | -4     | -3     | 10    | [[-3] * 3] * 10   |


    Scenario Outline: Min
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation          | a      | b      | count | result             |
        | 3       | min                | 2      | 3.5    | 10    | [[2] * 3] * 10     |
        | 3       | min                | 3.5    | 2      | 10    | [[2] * 3] * 10     |
        | 3       | min                | -3     | 2      | 10    | [[-3] * 3] * 10    |
        | 3       | min                | 2      | -3     | 10    | [[-3] * 3] * 10    |
        | 3       | min                | -4     | -3     | 10    | [[-4] * 3] * 10    |


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


    Scenario Outline: Multiplication
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation                      | a   | b    | count | result                |
        | 2       | private-private multiplication | 5   | 2    | 10    | [[10] * 2] * 10       |
        | 2       | private-private multiplication | 5   | 2.5  | 10    | [[12.5] * 2] * 10     |
        | 2       | private-private multiplication | 5   | -2.5 | 10    | [[-12.5] * 2] * 10    |
        | 2       | private-private multiplication | -5  | -2.5 | 10    | [[12.5] * 2] * 10     |
        | 2       | private-private multiplication | [5, 3.5]   | [2, 4]  | 10    | [[[10, 14]] * 2] * 10       |
        | 3       | private-private multiplication | 5   | 2    | 10    | [[10] * 3] * 10       |
        | 3       | private-private multiplication | 5   | 2.5  | 10    | [[12.5] * 3] * 10     |
        | 3       | private-private multiplication | 5   | -2.5 | 10    | [[-12.5] * 3] * 10    |
        | 3       | private-private multiplication | -5  | -2.5 | 10    | [[12.5] * 3] * 10     |
        | 3       | private-private multiplication | [5, 3.5]   | [2, 4]  | 10    | [[[10, 14]] * 3] * 10       |
        | 4       | private-private multiplication | 5   | 2    | 10    | [[10] * 4] * 10       |
        | 4       | private-private multiplication | 5   | 2.5  | 10    | [[12.5] * 4] * 10     |
        | 4       | private-private multiplication | 5   | -2.5 | 10    | [[-12.5] * 4] * 10    |
        | 4       | private-private multiplication | -5  | -2.5 | 10    | [[12.5] * 4] * 10     |
        | 4       | private-private multiplication | [5, 3.5]   | [2, 4]  | 10    | [[[10, 14]] * 4] * 10       |
        | 5       | private-private multiplication | 5   | 2    | 10    | [[10] * 5] * 10       |
        | 5       | private-private multiplication | 5   | 2.5  | 10    | [[12.5] * 5] * 10     |
        | 5       | private-private multiplication | 5   | -2.5 | 10    | [[-12.5] * 5] * 10    |
        | 5       | private-private multiplication | -5  | -2.5 | 10    | [[12.5] * 5] * 10     |
        | 5       | private-private multiplication | [5, 3.5]   | [2, 4]  | 10    | [[[10, 14]] * 5] * 10       |

