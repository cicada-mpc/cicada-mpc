Feature: Fields

    Scenario Outline: Subtraction
        Given a <field>
        When <b> is subtracted from <a> in the field the result should match <c>

        Examples:
        | field  | a         | b         | c        |
        | Field  | 1         | 1         | 0        |
        | Field  | 1         | 3         | -2       |
        | Field  | 1.2       | 3.5       | -2.3     |
        | Field  | 1.2       | 0         | 1.2      |
        | Field  | 0         | 1.2       | -1.2     |


    Scenario Outline: Negation
        Given a <field>
        When <a> is negated in the field the result should match <b>

        Examples:
        | field  | a         | b         |
        | Field  | 0         | 0         |
        | Field  | 3         | -3        |
        | Field  | 3.5       | -3.5      |
        | Field  | -3        | 3         |
        | Field  | -3.2      | 3.2       |


    Scenario Outline: Untruncated Matrix Vector Multiplication
        Given a <field>
        When matrix <A> and vector <x> are encoded and multiplied without truncation, the decoded result should match <y>

        Examples:
        | field | A                           | x                           | y                 |
        | Field | [[1,2,3],[4,5,6],[0,0,0]]   | [1,1,1]                     | [393216,983040,0] |
        | Field | [0, 1, 2, 3, 4, 5, 6, 7, 8] | [0, 1, 2, 3, 4, 5, 6, 7, 8] | 13369344          |


