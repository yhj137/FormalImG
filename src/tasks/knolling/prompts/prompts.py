PROMPT_GROUNDING = """
You are an expert visual grounding assistant for a formal verification system. 
Your task is to detect objects in the provided image and extract their visual attributes based strictly on the provided vocabulary.

### VOCABULARY CONSTRAINTS
You must ONLY use terms from the following lists. If an object's attribute is ambiguous, mixed, or not in the list, you must output "other".

- **Allowed Object Classes**: {object_classes}
- **Allowed Colors**: {colors}

### INSTRUCTIONS
1. **Detection**: Locate all objects visible in the image that belong to the "Allowed Object Classes" list.
2. **Attribute Extraction**: For each detected object, identify its dominant color using the lists above.
3. **Bounding Boxes**: Provide the bounding box as [xmin, ymin, xmax, ymax].
   - **IMPORTANT**: The coordinates must be **normalized integers from 0 to 1000**.
   - (0,0) is top-left, (1000,1000) is bottom-right.

### OUTPUT FORMAT
Output a valid JSON object strictly following this structure:

{{
  "objects": [
    {{
      "label": "One of {object_classes2}",
      "color": "One of {colors2}",
      "box_2d": [xmin, ymin, xmax, ymax]
    }},
    ...
  ]
}}
"""

prompts_generate = """
You are an expert proficient in First-Order Logic and Computer Vision data annotation. Your core task is to generate high-quality data pairs for evaluating advanced text-to-image models on their "structured compositional generalization capabilities" under the **Knolling (neat arrangement of items from an overhead view) style**. Both your input and output must be in strict JSON format.

#### Core Concept Definitions

*   **Dependency Closure**: A DSL expression can be decomposed into multiple independent **logical closures** connected by top-level `(and ...)`. A **logical closure** is defined as a minimal set of quantified variables formed by interlinking through binary predicates (such as `RightOf`, `Above`, `NextTo`). This association is **transitive**: if variable `?a` and `?b` are associated, and `?b` and `?c` are associated, then `?a`, `?b`, and `?c` belong to the same closure.
*   **Dependency Depth**: **Dependency Depth** is defined as **the total number of quantified variables (introduced by `exists`, `forall`) within a single logical closure**. The dependency depth of the entire DSL expression is the maximum dependency depth among all its logical closures.

#### DSL Domain
You must strictly adhere to the complete syntax and vocabulary of the following DSL.
{dsl}

#### Few-shot Examples

Below are compliant examples. Please study their JSON structure and content.

**[Knolling Style Example 1: Basic Spatial Chain]**
*   **Generation Parameters:**
{{
  "contained_vocabulary": ["laptop", "keyboard", "mouse"],
  "target_dependency_depth": {{
    "num_object_class": 3,
    "regular": 3,
    "count": 0
  }},
  "structure_control": {{
    "num_closures": 1,
    "closure_depths": [3],
    "exists_forall_struct": [["exists", "exists", "exists"]]
  }},
  "predicate_control": {{
    "required_predicates": ["RightOf", "AlignedHorizontally", "Has", "Is"]
  }}
}}

*   **Output:**
{{
  "natural_language_description": "Generate a Knolling-style image. The image contains a white laptop, a black keyboard, and a black mouse. The keyboard is located to the right of the laptop, the mouse is located to the right of the keyboard, and these three objects are aligned horizontally.",
  "dsl_representation": "(exists ?laptop (exists ?keyboard (exists ?mouse (and (Is ?laptop 'laptop') (Has ?laptop 'white') (Is ?keyboard 'keyboard') (Has ?keyboard 'black') (Is ?mouse 'mouse') (Has ?mouse 'black') (RightOf ?keyboard ?laptop) (RightOf ?mouse ?keyboard) (AlignedHorizontally ?laptop ?keyboard) (AlignedHorizontally ?keyboard ?mouse)))))"
}}

**[Knolling Style Example 2: Universal Quantifier Constraint]**
*   **Generation Parameters:**
{{
  "contained_vocabulary": ["wrench", "screwdriver"],
  "target_dependency_depth": {{
    "num_object_class": 2,
    "regular": 2,
    "count": 0
  }},
  "structure_control": {{
    "num_closures": 1,
    "closure_depths": [2],
    "exists_forall_struct": [["forall", "exists"]]
  }},
  "predicate_control": {{
    "required_predicates": ["LeftOf", "Has", "Is"]
  }}
}}

*   **Output:**
{{
  "natural_language_description": "Generate a Knolling-style image. For every wrench in the image, there is a red screwdriver to its left.",
  "dsl_representation": "(and (forall ?w (implies (Is ?w 'wrench') (exists ?d (and (Is ?d 'screwdriver') (Has ?d 'red') (LeftOf ?d ?w))))))"
}}

**[Knolling Style Example 3: Vertical Alignment & Comparison]**
*   **Generation Parameters:**
{{
  "contained_vocabulary": ["book", "ruler", "pen", "calculator"],
  "target_dependency_depth": {{
    "num_object_class": 4,
    "regular": 3,
    "count": 0
  }},
  "structure_control": {{
    "num_closures": 2,
    "closure_depths": [3, 1],
    "exists_forall_struct": [["exists", "exists", "exists"], ["exists"]]
  }},
  "predicate_control": {{
    "required_predicates": ["Above", "AlignedVertically", "LargerThan", "OnRightSide", "Is"]
  }}
}}

*   **Output:**
{{
  "natural_language_description": "Generate a Knolling-style image. The scene contains a book, a ruler, a calculator, and a pen. The book is above the ruler, the ruler is above the pen, and they are aligned vertically. The book is visually larger than the pen. The calculator is located on the right side of the scene.",
  "dsl_representation": "(and (exists ?b (exists ?ruler (exists ?pen (and (Is ?b 'book') (Is ?ruler 'ruler') (Is ?pen 'pen') (Above ?b ?ruler) (Above ?ruler ?pen) (AlignedVertically ?b ?ruler) (AlignedVertically ?ruler ?pen) (LargerThan ?b ?pen))))) (exists ?c (and (Is ?c 'calculator') (OnRightSide ?c))))"
}}

**[Knolling Style Example 4: Complex Spatial Chain]**
*   **Generation Parameters:**
{{
  "contained_vocabulary": ["notebook", "coffee_cup", "pen", "keyboard", "mouse"],
  "target_dependency_depth": {{
    "num_object_class": 5,
    "regular": 5,
    "count": 0
  }},
  "structure_control": {{
    "num_closures": 1,
    "closure_depths": [5],
    "exists_forall_struct": [["exists", "exists", "exists", "exists", "exists"]]
  }},
  "predicate_control": {{
    "required_predicates": ["Above", "Below", "RightOf", "AlignedVertically", "Is"]
  }}
}}

*   **Output:**
{{
  "natural_language_description": "Generate a Knolling-style image. The scene features a notebook as the center. Directly above the notebook is a cup of coffee, and directly below is a keyboard; these three are aligned vertically. To the right of the coffee cup is a pen. To the right of the keyboard is a mouse. Additionally, the pen and the mouse also need to be vertically aligned.",
  "dsl_representation": "(exists ?notebook (exists ?coffee_cup (exists ?pen (exists ?keyboard (exists ?mouse (and (Is ?notebook 'notebook') (Is ?coffee_cup 'coffee_cup') (Is ?pen 'pen') (Is ?keyboard 'keyboard') (Is ?mouse 'mouse') (Above ?coffee_cup ?notebook) (Below ?keyboard ?notebook) (RightOf ?pen ?coffee_cup) (RightOf ?mouse ?keyboard) (AlignedVertically ?notebook ?coffee_cup) (AlignedVertically ?notebook ?keyboard) (AlignedVertically ?pen ?mouse)))))))"
}}

---
#### Your Task

Now, please strictly follow the JSON format to generate a **brand new**, **logical** data pair regarding a **Knolling layout** based on the specified parameters below. Please exercise your creativity and logical reasoning skills; do not simply repeat or stitch together the above examples.
You may only use the predicates specified in `required_predicates`.

*   **Generation Parameters:**
{instruction}

*   **Output:**
{{
  "natural_language_description": "...",
  "dsl_representation": "..."
}}

Please output a complete, comment-free JSON object directly. Do not include any additional explanations or Markdown code block markers.
"""

prompt_style = """
[Generation Rules and Style Definition]
1. Art Style: Please generate a standard Knolling style (flat lay organization) image.
   - Perspective: Must be a strictly vertical 90-degree top-down / overhead view.
   - Layout: Objects should be neatly arranged with space between them. Overlapping or occlusion of objects is strictly forbidden.
   - Background: A clean, flat background (white, light gray, or pale yellow is recommended).

2. Spatial Position Definition (Crucial):
   To ensure proper spacing and avoid overlap, positional descriptions are determined by the relative relationship between an **object's boundary and a reference object's center point**:
   
   - [On the left side / right side / top / bottom]: Refers to the object's geometric center being located in the corresponding half of the entire frame.
   - [In the Center (InCenter)]: Refers to the object's center point being strictly within the central cell of a 3x3 grid dividing the frame.

   **Relative Position Determination Logic:**
   - [A is to the left of B (LeftOf)]: The X-coordinate of A's **right edge** must be less than the X-coordinate of B's **center point**.
   - [A is to the right of B (RightOf)]: The X-coordinate of A's **left edge** must be greater than the X-coordinate of B's **center point**.
   - [A is above B (Above)]: The Y-coordinate of A's **bottom edge** must be less than the Y-coordinate of B's **center point** (visually, A's bottom is higher than B's center).
   - [A is below B (Below)]: The Y-coordinate of A's **top edge** must be greater than the Y-coordinate of B's **center point** (visually, A's top is lower than B's center).
   
   - [Horizontally Aligned]: The Y-coordinates of the objects' center points are nearly identical.
   - [Vertically Aligned]: The X-coordinates of the objects' center points are nearly identical.

3. Object Attributes:
   - Please ensure object color descriptions are consistent.
   - Size Relations: If 'A is larger than B' is described, ensure the projected area of A in the frame is greater than that of B.

[The specific description is as follows]:
"""

prompt_style_diffusion = """
Generate a clean knolling-style flat lay image.

• Perspective: strict 90-degree top-down view.
• Layout: all objects are neatly arranged with clear spacing between them.
  No overlapping or touching objects.
• Background: solid, clean background (white, light gray, or pale yellow).

• Composition:
  - Objects are placed in clear rows or columns.
  - Relative positions are obvious (left / right / above / below).
  - Objects that are described as aligned should appear visually aligned.

• Object rules:
  - Colors are consistent with the description.
  - Size relationships are respected (larger objects clearly appear larger).

[Scene description:]
"""

prompt_style_llm = """
**[Role and Task Definition]**

You are an AI Scene Planner serving a text-to-image generation system. Your core task is to accurately convert a user's natural language scene description into a structured JSON object. This JSON object defines the attributes, precise 2D bounding boxes, and spatial relationships of every object in the scene. You must strictly follow all the rules and logic defined below to generate this JSON.

**[1. Canvas and Coordinate System]**

1.  **Canvas Size**: All calculations are based on a virtual `1000x1000` pixel canvas.
2.  **Coordinate Origin**: The coordinate system's origin `(0, 0)` is at the top-left corner of the canvas.
3.  **Coordinate Range**: All `box_2d` coordinate values (x_min, y_min, x_max, y_max) must be integers within the range `[0, 999]`.

**[2. Output Format]**

Your output must be a single, well-formatted JSON object, without any explanatory text outside of the JSON itself. The structure is as follows:

```json
[
    {{
        "label": "object_label",
        "color": "object_color",
        "box_2d": [x_min, y_min, x_max, y_max]
    }}
]
```

**[3. Core Principles of Art Style and Layout: Knolling]**

The layout of all objects must adhere to the core principles of the Knolling style:

1.  **Perspective**: Must be a strictly vertical 90-degree top-down / overhead view.
2.  **Layout**: Objects should be neatly arranged. Most importantly, **the bounding boxes (`box_2d`) of any two objects must never overlap**. There must be clear spacing between all objects.
3.  **Background**: The background is a solid color. This does not affect the JSON generation for the objects, but you should be aware that objects are placed independently.

**[4. Spatial Position Definition (Crucial Logic)]**

These are the most critical rules you must follow when generating `box_2d` coordinates.

**4.1. Basic Definitions**

-   The bounding box of an object `A` is `[A_xmin, A_ymin, A_xmax, A_ymax]`.
-   The coordinates of the center point `A_center` of an object `A` are:
    -   `A_center_x = (A_xmin + A_xmax) / 2`
    -   `A_center_y = (A_ymin + A_ymax) / 2`

**4.2. Absolute Position Definition (based on object center point)**

-   **[On the left side]**: The object's `center_x` < 500.
-   **[On the right side]**: The object's `center_x` > 500.
-   **[On the top side]**: The object's `center_y` < 500.
-   **[On the bottom side]**: The object's `center_y` > 500.
-   **[In the center]**: The object's center point `(center_x, center_y)` must be strictly within the central area of a 3x3 grid dividing the canvas, i.e., `333 < center_x < 666` and `333 < center_y < 666`.

**4.3. Relative Position Determination Logic (based on "object boundary" and "reference object center point")**

This is the **sole standard** for determining the relative positions between objects:

-   **[A is to the left of B]**: A's **right edge** (`A_xmax`) must be less than B's **center point X-coordinate** (`B_center_x`).
-   **[A is to the right of B]**: A's **left edge** (`A_xmin`) must be greater than B's **center point X-coordinate** (`B_center_x`).
-   **[A is above B]**: A's **bottom edge** (`A_ymax`) must be less than B's **center point Y-coordinate** (`B_center_y`).
-   **[A is below B]**: A's **top edge** (`A_ymin`) must be greater than B's **center point Y-coordinate** (`B_center_y`).

**4.4. Alignment**

-   **[Horizontally Aligned]**: The `center_y` coordinates of multiple objects should be nearly identical.
-   **[Vertically Aligned]**: The `center_x` coordinates of multiple objects should be nearly identical.

**[5. Learning from an Example]**

**User Description**: "Generate a Knolling style image. There is a black phone in the center of the frame, another phone on the left side, and a blue pen on the right side."

**Your Correct Output**:
```json
[
    {{
        "label": "phone",
        "color": "white",
        "box_2d": [84, 232, 337, 759]
    }},
    {{
        "label": "phone",
        "color": "black",
        "box_2d": [405, 242, 668, 759]
    }},
    {{
        "label": "pen",
        "color": "blue",
        "box_2d": [827, 249, 874, 762]
    }}
]
```

**[6. Object and Color Vocabularies]**

The object labels you can use in your output are: {objs}

The color labels you can use in your output are: {colors}

---

**[Begin Task]**

Now, strictly following all the rules above, generate the corresponding JSON output for the following user description.

**User Description:**
"""

prompt_r2i = """[Task Instruction]
The attached image is a **Structural Blueprint** only. 
Your task is to generate a **brand new** photorealistic Knolling photo based on the object positions defined in this blueprint.

[CRITICAL RULES - READ CAREFULLY]
1. **INVISIBLE BLUEPRINT**: The black bounding boxes, text labels, and gray box backgrounds in the reference image are **GUIDES ONLY**. 
   - **DO NOT** render the black rectangular outlines in the final image.
   - **DO NOT** render the text labels (e.g., "shoe", "phone") in the final image.
   - **DO NOT** render the different colored background patches.
   
2. **UNIFIED BACKGROUND**: The final image must have a **single, seamless, uniform background** (pure white or light gray) across the entire image. There should be no visible "patches" or "cards" behind the objects.

[Execution Steps]
1. **Extract Information**: Read the text label inside each box to know the object (e.g., "shoe") and its color/attribute.
2. **Re-Imagine**: Imagine the reference image disappears and is replaced by a clean white table.
3. **Place Objects**: Place the real, 3D photorealistic objects at the exact center positions indicated by the blueprint boxes.
4. **Scale**: Ensure the objects fill the area defined by the boxes but do not look like flat stickers.

[Art Style]
- Photorealistic product photography.
- 90-degree top-down view.
- Soft shadows, no harsh outlines.
"""

prompt_layout = """[Task Instruction]
You are to generate an image based on the following rules and the appended JSON data. Adherence to these instructions is mandatory.

**1. Core Art Style and Rules:**
*   **Art Style:** Standard **Knolling** (flat lay organization).
*   **Perspective:** A strict **90-degree top-down / overhead view** is required.
*   **Layout:** All objects must be **neatly arranged** with clear, visible space between them. **Overlapping or occlusion of objects is strictly forbidden.**
*   **Background:** The background must be a **clean, flat, solid color** (white, light gray, or pale yellow is recommended).

**2. Layout Instructions and JSON Data Interpretation:**
The image composition is explicitly defined by the JSON object provided below. You must interpret and render it according to the following logic:
*   **Coordinate System:** The entire canvas is defined by a coordinate system ranging from `[0, 0]` at the top-left corner to `[1000, 1000]` at the bottom-right corner.
*   **Object Definition:** The JSON contains an `objects` list. Each element in this list represents a single object to be drawn.
    *   `"label"`: This specifies the **name** of the object to render (e.g., "suitcase," "pizza").
    *   `"color"`: This defines the object's **primary color**.
    *   `"box_2d"`: This is an array with the format `[x_min, y_min, x_max, y_max]`. It defines the object's **exact bounding box**. You must render the object so that it is contained entirely and precisely within this specified box on the canvas.

[BEGIN JSON DATA]
"""

prompt_check = """You are an extremely rigorous first-order logic analyst and data quality verification expert. Your task is to review a data pair consisting of a natural language description (NL) and a Domain-Specific Language (DSL) representation to ensure its logical soundness and the consistency between the two. Your input and output must both be in strict JSON format.

#### DSL Domain
You must strictly adhere to the complete syntax and vocabulary of the following DSL for your analysis.
{dsl}

#### Core Review Principles

Your review process consists of two core steps, which must be executed in order:

**1. Contradiction Check:**
First, you must determine if the DSL expression itself contains an internal contradiction, making it **unsatisfiable** in any two-dimensional image. Mainly check for two types of contradictions:
*   **Logical Paradoxes:** For example, using the `forall` quantifier leads to infinite recursive generation (e.g., 'for every A, there exists a B, and next to B, there is another A'). This is impossible to realize in a finite image space.
*   **Geometric Paradoxes:** Describing spatial relationships that are physically impossible to coexist. For example, simultaneously requiring two objects to be `(RightOf ?a ?b)` and `(AlignedVertically ?a ?b)`.

If any such contradiction is detected, your task ends immediately.

**2. Alignment Check:**
You only proceed to this check if the DSL has **no** internal contradictions. The core principle of this step is:
**The DSL expression must not introduce any logical or spatial constraints that are not explicitly stated or strongly implied in the NL.**

In other words, the set of valid scenes defined by the DSL must be a **superset** or an **equal set** of the scenes described by the NL, and never a **subset**.

*   **Aligned Example:**
    *   NL: "A picture with a red pen and a book."
    *   DSL: `(exists ?p (exists ?b (and (Is ?p 'pen') (Has ?p 'red') (Is ?b 'book'))))`
    *   **Analysis:** Aligned.

*   **Misaligned Examples (DSL is more specific than NL):**
    *   NL: "A picture with two books."
    *   DSL: `(exists ?b1 (exists ?b2 (and (Is ?b1 'book') (Is ?b2 'book') (RightOf ?b2 ?b1))))`
    *   **Analysis:** Misaligned. The NL specifies no spatial relationship, but the DSL arbitrarily adds the `(RightOf ?b2 ?b1)` constraint.
    *   NL: "Two laptops and two lighters are arranged in a 2x2 grid."
    *   DSL: `(exists ?l1 .. (and .. (RightOf ?g1 ?l1) (Below ?l2 ?l1) (RightOf ?g2 ?l2)))`
    *   **Analysis:** Misaligned. The "2x2 grid" in the NL is ambiguous and allows for multiple specific layouts. However, the DSL specifies only **one** of these layouts, making the DSL's constraints stronger than the NL's.

#### Output Format
You must return a strict JSON object containing the following three fields:
*   `"is_contradictory"` (boolean): `true` if the DSL contains an internal contradiction, otherwise `false`.
*   `"is_aligned"` (boolean | null):
    *   If `"is_contradictory"` is `true`, this field must be `null`.
    *   If the DSL is not contradictory, determine if the NL and DSL are aligned. `true` for aligned, `false` for misaligned.
*   `"corrected_nl_description"` (string | null):
    *   If `"is_contradictory"` is `true`, or if `"is_aligned"` is `true`, this field must be `null`.
    *   Only when `"is_aligned"` is `false`, this field must contain a **revised, clear, and unambiguous natural language description that perfectly corresponds to the given DSL.**

---
#### Few-shot Review Examples

**[Example 1: Logical Paradox]**
*   **Input:**
{{
  "natural_language_description": "Generate a Knolling-style image. For every pizza in the image, there exists a game controller to its right, to the right of which is another game controller, and to the right of that game controller is another pizza.",
  "dsl_representation": "(and (forall ?p1 (implies (Is ?p1 'pizza') (exists ?g1 (exists ?g2 (exists ?p2 (and (Is ?g1 'game_controller') (Is ?g2 'game_controller') (Is ?p2 'pizza') (RightOf ?g1 ?p1) (RightOf ?g2 ?g1) (RightOf ?p2 ?g2))))))))"
}}
*   **Output:**
{{
  "is_contradictory": true,
  "is_aligned": null,
  "corrected_nl_description": null
}}

**[Example 2: Geometric Paradox]**
*   **Input:**
{{
  "natural_language_description": "Generate a Knolling-style image. There is a black calculator, a red tie, and a watch. They are placed in order from left to right, and the calculator and the watch must also be vertically aligned.",
  "dsl_representation": "(exists ?c (exists ?t (exists ?w (and (Is ?c 'calculator') (Has ?c 'black') (Is ?t 'tie') (Is ?w 'watch') (RightOf ?t ?c) (RightOf ?w ?t) (AlignedVertically ?c ?w))))))"
}}
*   **Output:**
{{
  "is_contradictory": true,
  "is_aligned": null,
  "corrected_nl_description": null
}}

**[Example 3: Misaligned]**
*   **Input:**
{{
    "natural_language_description": "Generate a Knolling-style image. At the bottom of the image, there is a horizontally aligned row of items, from left to right: a pen, a watch, a pen, a watch, and a pen. In the left half of the image, for any pan, there is a knife placed in each of the four cardinal directions (above, below, left, right), forming a cross shape. Additionally, there are two laptops and two lighters arranged in a 2x2 grid.",
    "dsl_representation": "(and (exists ?p1 (exists ?w1 (exists ?p2 (exists ?w2 (exists ?p3 (and (Is ?p1 'pen') (Is ?w1 'watch') (Is ?p2 'pen') (Is ?w2 'watch') (Is ?p3 'pen') (OnBottomSide ?p1) (RightOf ?w1 ?p1) (RightOf ?p2 ?w1) (RightOf ?w2 ?p2) (RightOf ?p3 ?w2) (AlignedHorizontally ?p1 ?w1) (AlignedHorizontally ?w1 ?p2) (AlignedHorizontally ?p2 ?w2) (AlignedHorizontally ?w2 ?p3))))))) (forall ?pan (implies (and (Is ?pan 'pan') (OnLeftSide ?pan)) (exists ?k1 (exists ?k2 (exists ?k3 (exists ?k4 (and (Is ?k1 'knife') (Is ?k2 'knife') (Is ?k3 'knife') (Is ?k4 'knife') (RightOf ?k1 ?pan) (Below ?k2 ?pan) (LeftOf ?k3 ?pan) (Above ?k4 ?pan)))))))) (exists ?l1 (exists ?g1 (exists ?l2 (exists ?g2 (and (Is ?l1 'laptop') (Is ?g1 'lighter') (Is ?l2 'laptop') (Is ?g2 'lighter') (RightOf ?g1 ?l1) (Below ?l2 ?l1) (RightOf ?g2 ?l2)))))))"
}}
*   **Output:**
{{
  "is_contradictory": false,
  "is_aligned": false,
  "corrected_nl_description": "Generate a Knolling-style image. At the bottom of the image, there is a horizontally aligned row of items, from left to right: a pen, a watch, a pen, a watch, and a pen. In the left half of the image, for any pan, there is a knife to its right, a knife below it, a knife to its left, and a knife above it. Additionally, there exists a laptop with a lighter to its right, and below that laptop is another laptop, which also has a lighter to its right."
}}

**[Example 4: Qualified Sample]**
*   **Input:**
{{
  "natural_language_description": "Generate a Knolling-style image. There is a white laptop, and to its right is a black keyboard.",
  "dsl_representation": "(exists ?laptop (exists ?keyboard (and (Is ?laptop 'laptop') (Has ?laptop 'white') (Is ?keyboard 'keyboard') (Has ?keyboard 'black') (RightOf ?keyboard ?laptop))))"
}}
*   **Output:**
{{
  "is_contradictory": false,
  "is_aligned": true,
  "corrected_nl_description": null
}}

---
#### Your Task

Now, review the following data pair and return your analysis strictly in the JSON format described above.

*   **Sample to Check:**
{sample_to_check}

*   **Output:**
{{
  "is_contradictory": ...,
  "is_aligned": ...,
  "corrected_nl_description": ...
}}
Directly output a single, complete JSON object without any comments, explanations, or Markdown code block markers.
"""
