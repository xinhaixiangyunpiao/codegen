// service class
class IService{

};

class A_service: public IService{
    public:
        virtual void CreateInstance(const int& b);
        virtual void A_function(int a) = 0;
        virtual double* A_function(float c) = 0;
};

class B_service: public IService{
    public:
        virtual void B_function(int a) = 0;
        virtual double& B_function(float* c) = 0;
};

// normal class
class C{
    private:
        char c = 'a';
        float b = 4.2;
        int a = 3;
        double d;
        bool x = false;
    public:
        int getA(void);
        void setB(float b);
};