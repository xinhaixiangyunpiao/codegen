// MODEL A and MODEL B VIEWMODEL
// viewmodel base class
#define ICoreFramework int
namespace spark{
    template <class T>
    class handle{
        T a;
    };
};

class IViewModel{

};

class A_viewmodel: public IViewModel{
    public:
        virtual void CreateInstance(const spark::handle<ICoreFramework>& a, const int& b);
        virtual void setA(int a);
        virtual double getB(void);
};

class B_viewmodel: public IViewModel{
    public:
        virtual void CreateInstance(const spark::handle<ICoreFramework>& a, const int& b, const float& c);
        virtual void setG(double g);
        virtual char getI(void);
};