// some enum
enum color_set1 {RED, BLUE, WHITE, BLACK};
enum week {Sun, Mon, Tue, Wed, Thu, Fri, Sat};
enum fruit_set {apple, orange, banana=1, peach, grape};

// some MODEL
class A{
    public:
        int a = 1;
        double b = 2;
        char c = 'a';
        long d = 3;
        float e = 5.0;
};

class B{
    public:
        A f;
        double g;
        float* h;
        char i = 'u';
};
